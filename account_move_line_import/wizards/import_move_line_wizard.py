# Copyright 2009-2023 Noviat
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64
import csv
import io
import json
import logging
import os
import time
from datetime import datetime

import xlrd

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .import_wizard_helpers import (
    cell2bool,
    cell2char,
    cell2date,
    cell2float,
    cell_is_int,
    dialect2dict,
    str2float,
    str2int,
)

_logger = logging.getLogger(__name__)

_FIELD_TYPE_MAP = {
    "text": "char",
    "monetary": "float",
}


class AccountMoveLineImport(models.TransientModel):
    _name = "aml.import"
    _description = "Import account move lines"

    aml_data = fields.Binary(string="File", required=True)
    aml_fname = fields.Char(string="Filename")
    file_type = fields.Selection(
        selection=[("csv", "csv"), ("xls", "xls"), ("xlsx", "xlsx")]
    )
    sheet = fields.Char(
        help="Specify the Excel sheet."
        "\nIf not specified the first sheet will be retrieved."
    )
    dialect = fields.Char(help="JSON dictionary to store the csv dialect")
    csv_separator = fields.Selection(
        selection=[(",", ", (comma)"), (";", "; (semicolon)")], string="CSV Separator"
    )
    decimal_separator = fields.Selection(
        selection=[(".", ". (dot)"), (",", ", (comma)")],
        default=".",
    )
    codepage = fields.Char(
        string="Code Page",
        help="Code Page of the system that has generated the csv file."
        "\nE.g. Windows-1252, utf-8",
    )
    warning = fields.Text(readonly=True)
    note = fields.Text("Log")

    @api.onchange("aml_fname")
    def _onchange_aml_fname(self):
        if not self.aml_fname:
            return
        name, ext = os.path.splitext(self.aml_fname)
        ext = ext[1:]
        if ext not in ["csv", "xls", "xlsx"]:
            self.warning = _(
                "<b>Incorrect file format !</b>"
                "<br>Only files of type csv and xls(x) are supported."
            )
            return
        else:
            self.file_type = ext
            self.warning = False
        if ext == "csv":
            self.codepage = self._default_csv_codepage()
        else:
            self.codepage = self._default_xls_codepage()

    def _default_csv_codepage(self):
        return "utf-8"

    def _default_xls_codepage(self):
        return "utf-16le"

    @api.onchange("sheet")
    def _onchange_sheet(self):
        self.warning = False

    @api.onchange("aml_data")
    def _onchange_aml_data(self):
        if self.file_type == "csv" and self.aml_data:
            self._guess_dialect()

    def _guess_dialect(self):
        # the self.aml_data is type 'str' during the onchange processing,
        # hence we convert into bytes so that we can try to determine the
        # csv dialect
        if not isinstance(self.aml_data, bytes):
            lines = bytes(self.aml_data, encoding=self.codepage)
        else:
            lines = self.aml_data
        lines = base64.decodebytes(lines)
        # convert windows & mac line endings to unix style
        lines = lines.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        first_lines = lines.split(b"\n", 3)
        try:
            sample = b"\n".join(first_lines[:3]).decode(self.codepage)
            dialect = csv.Sniffer().sniff(sample, delimiters=";,")
        except Exception:
            dialect = csv.Sniffer().sniff('"header 1";"header 2";\n')
            if b";" in first_lines[0]:
                dialect.delimiter = ";"
            elif b"," in first_lines[0]:
                dialect.delimiter = ","
        self.csv_separator = dialect.delimiter
        dialect.lineterminator = "\n"
        if self.csv_separator == ";":
            self.decimal_separator = ","
        if lines[:3] == b"\xef\xbb\xbf":
            self.codepage = "utf-8-sig"
        dialect_dict = dialect2dict(dialect)
        self.dialect = json.dumps(dialect_dict)

    @api.onchange("csv_separator")
    def _onchange_csv_separator(self):
        if self.csv_separator and self.aml_data:
            dialect_dict = json.loads(self.dialect)
            if dialect_dict["delimiter"] != self.csv_separator:
                dialect_dict["delimiter"] = self.csv_separator
                self.dialect = json.dumps(dialect_dict)

    def _read_csv(self, wiz_dict, data):
        # convert windows & mac line endings to unix style
        lines = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        lines, header = self._remove_leading_lines(
            wiz_dict, lines.decode(self.codepage)
        )
        dialect_dict = json.loads(self.dialect)
        header_fields = next(csv.reader(io.StringIO(header), **dialect_dict))
        wiz_dict["header_fields"] = self._process_header(wiz_dict, header_fields)
        reader = csv.DictReader(
            io.StringIO(lines), fieldnames=wiz_dict["header_fields"], **dialect_dict
        )
        return reader

    def _read_xls(self, wiz_dict, data):  # noqa: C901
        wb = xlrd.open_workbook(file_contents=data)
        if self.sheet:
            try:
                sheet = wb.sheet_by_name(self.sheet)
            except xlrd.XLRDError as e:
                self.warning = _("Error while reading Excel sheet: <br>%(err)s") % {
                    "err": e
                }
                return
        else:
            sheet = wb.sheet_by_index(0)
        lines = []
        header = False
        for ri in range(sheet.nrows):
            err_msg = ""
            line = {}
            ln = sheet.row_values(ri)
            if not ln or ln and ln[0] == "#":
                continue
            if not header:
                header = [x.lower() for x in ln]
                wiz_dict["header_fields"] = self._process_header(wiz_dict, header)
            else:
                for ci, hf in enumerate(wiz_dict["header_fields"]):
                    line[hf] = False
                    val = False
                    cell = sheet.cell(ri, ci)
                    if hf in wiz_dict["skip_fields"]:
                        continue
                    if cell.ctype in [xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_BLANK]:
                        continue
                    if cell.ctype == xlrd.XL_CELL_ERROR:
                        if err_msg:
                            err_msg += "\n"
                        err_msg += _(
                            "Incorrect value '%(val)s' for field '%(hf)s' !"
                        ) % {
                            "cell": cell.value,
                            "hf": hf,
                        }
                        continue

                    fmt = wiz_dict["field_methods"][hf]["field_type"]

                    if fmt == "char":
                        val = cell2char(cell)

                    elif fmt == "float":
                        val = cell2float(cell)

                    elif fmt == "integer":
                        if cell.value:
                            if cell_is_int(cell):
                                val = int(cell.value)
                            else:
                                if err_msg:
                                    err_msg += "\n"
                                err_msg += _(
                                    "Incorrect value '%(val)s' "
                                    "for field '%(hf)s' of type %(fmt)s !"
                                ) % {
                                    "cell": cell.value,
                                    "hf": hf,
                                    "fmt": fmt.capitalize(),
                                }

                    elif fmt == "many2one":
                        if cell.value:
                            if cell_is_int(cell):
                                val = int(cell.value)
                            else:
                                val = cell2char(cell)

                    elif fmt == "boolean":
                        val = cell2bool(cell)
                        if val is None:
                            if err_msg:
                                err_msg += "\n"
                            err_msg += _(
                                "Incorrect value '%(val)s' "
                                "for field '%(hf)s' of type Boolean !"
                            ) % {"val": cell.value, "hf": hf}

                    elif fmt == "date":
                        if cell.value:
                            val = cell2date(cell, wb.datemode)
                            if val is None:
                                if err_msg:
                                    err_msg += "\n"
                                err_msg += _(
                                    "Incorrect value '%(val)s' "
                                    "for field '%(hf)s' of type Date, "
                                    "it should be YYYY-MM-DD !"
                                ) % {"val": cell.value, "hf": hf}

                    elif fmt == "many2many":
                        if cell.ctype == xlrd.XL_CELL_TEXT:
                            val = cell.value
                        else:
                            if err_msg:
                                err_msg += "\n"
                            err_msg += _(
                                "Incorrect value '%(val)s' "
                                "for field '%(hf)s', "
                                "it should be a comma separated string !"
                            ) % {"val": cell.value, "hf": hf}

                    else:
                        _logger.error(
                            "%s, field '%s', Unsupported format '%s'",
                            self._name,
                            hf,
                            fmt,
                        )
                        raise NotImplementedError

                    if val:
                        line[hf] = val

                if err_msg:
                    self._log_line_error(wiz_dict, line, err_msg)

                if line:
                    lines.append(line)

        return lines

    def aml_import(self):
        time_start = time.time()

        move = self.env["account.move"].browse(self.env.context["active_id"])
        accounts = self.env["account.account"].search(
            [("deprecated", "=", False), ("company_id", "=", move.company_id.id)]
        )
        wiz_dict = {
            "err_log": "",
            "accounts_dict": {a.code: a.id for a in accounts},
        }
        self._get_orm_fields(wiz_dict)
        data = base64.decodebytes(self.aml_data)
        if self.file_type == "csv":
            lines = self._read_csv(wiz_dict, data)
        elif self.file_type in ["xls", "xlsx"]:
            lines = self._read_xls(wiz_dict, data)
        else:
            raise NotImplementedError
        if self.warning:
            module = __name__.split("addons.")[1].split(".")[0]
            view = self.env.ref("%s.aml_import_view_form" % module)
            return {
                "name": _("Import File"),
                "res_id": self.id,
                "view_type": "form",
                "view_mode": "form",
                "res_model": "aml.import",
                "view_id": view.id,
                "target": "new",
                "type": "ir.actions.act_window",
                "context": self.env.context,
            }

        move_lines = []
        for line in lines:

            aml_vals = {}

            # process input fields
            for i, hf in enumerate(wiz_dict["header_fields"]):
                if (
                    i == 0
                    and isinstance(line[hf], str)
                    and line[hf]
                    and line[hf][0] == "#"
                ):
                    # lines starting with # are considered as comment lines
                    break
                if hf in wiz_dict["skip_fields"]:
                    continue
                if line[hf] in ["", False]:
                    continue

                if wiz_dict["field_methods"][hf].get("orm_field"):
                    wiz_dict["field_methods"][hf]["method"](
                        wiz_dict,
                        hf,
                        line,
                        move,
                        aml_vals,
                        orm_field=wiz_dict["field_methods"][hf]["orm_field"],
                    )
                else:
                    wiz_dict["field_methods"][hf]["method"](
                        wiz_dict, hf, line, move, aml_vals
                    )

            if aml_vals:
                self._process_line_vals(wiz_dict, line, move, aml_vals)
                move_lines.append(aml_vals)

        vals = [(0, 0, r) for r in move_lines]
        vals = self._process_vals(wiz_dict, move, vals)

        if wiz_dict["err_log"]:
            self.note = wiz_dict["err_log"]
            module = __name__.split("addons.")[1].split(".")[0]
            result_view = self.env.ref("%s.aml_import_view_form_result" % module)
            return {
                "name": _("Import File result"),
                "res_id": self.id,
                "view_type": "form",
                "view_mode": "form",
                "res_model": "aml.import",
                "view_id": result_view.id,
                "target": "new",
                "type": "ir.actions.act_window",
            }
        else:
            move.with_context(check_move_validity=True).write({"line_ids": vals})
            import_time = time.time() - time_start
            _logger.warning(
                "account.move %s import time = %.3f seconds", move.name, import_time
            )
            return {"type": "ir.actions.act_window_close"}

    def _remove_leading_lines(self, wiz_dict, lines):
        """remove leading blank or comment lines"""
        input_buffer = io.StringIO(lines)
        header = False
        while not header:
            ln = next(input_buffer)
            if not ln or ln and ln[0] in [self.csv_separator, "#"]:
                continue
            else:
                header = ln.lower()
        if not header:
            raise UserError(_("No header line found in the input file !"))
        output = input_buffer.read()
        return output, header

    def _input_fields(self):
        """
        Extend this dictionary if you want to add support for
        fields requiring pre-processing before being added to
        the move line values dict.

        TODO: add support for taxes.
        """
        res = {
            "account": {"method": self._handle_account, "field_type": "char"},
            "account_id": {"required": True},
            "debit": {"method": self._handle_debit, "field_type": "float"},
            "credit": {"method": self._handle_credit, "field_type": "float"},
            "partner": {"method": self._handle_partner, "field_type": "char"},
            "product": {"method": self._handle_product, "field_type": "char"},
            "date_maturity": {
                "method": self._handle_date_maturity,
                "field_type": "date",
            },
            "due date": {"method": self._handle_date_maturity, "field_type": "date"},
            "currency": {"method": self._handle_currency, "field_type": "char"},
            "analytic account": {
                "method": self._handle_analytic_account,
                "field_type": "char",
            },
            "tax grids": {"method": self._handle_tax_grids, "field_type": "many2many"},
        }
        return res

    def _get_orm_fields(self, wiz_dict):
        aml_mod = self.env["account.move.line"]
        orm_fields = aml_mod.fields_get()
        blacklist = models.MAGIC_COLUMNS + [aml_mod.CONCURRENCY_CHECK_FIELD]
        wiz_dict["orm_fields"] = {
            f: orm_fields[f]
            for f in orm_fields
            if f not in blacklist and not orm_fields[f].get("depends")
        }

    def _process_header(self, wiz_dict, header_fields):

        wiz_dict["field_methods"] = self._input_fields()
        wiz_dict["skip_fields"] = []

        # header fields after blank column are considered as comments
        column_cnt = 0
        for cnt in range(len(header_fields)):
            if header_fields[cnt] == "":
                column_cnt = cnt
                break
            elif cnt == len(header_fields) - 1:
                column_cnt = cnt + 1
                break
        header_fields = header_fields[:column_cnt]

        # check for duplicate header fields
        header_fields2 = []
        for hf in header_fields:
            if hf in header_fields2:
                raise UserError(
                    _(
                        "Duplicate header field '%s' found !"
                        "\nPlease correct the input file."
                    )
                    % hf
                )
            else:
                header_fields2.append(hf)

        for hf in header_fields:

            if hf in wiz_dict["field_methods"] and wiz_dict["field_methods"][hf].get(
                "method"
            ):
                if not wiz_dict["field_methods"][hf].get("field_type"):
                    raise UserError(
                        _(
                            "Programming Error:\nMissing formatting info for column '%s'."
                        )
                        % hf
                    )
                continue

            if hf not in wiz_dict["orm_fields"] and hf not in [
                wiz_dict["orm_fields"][f]["string"].lower()
                for f in wiz_dict["orm_fields"]
            ]:
                _logger.error(
                    _(
                        "%(name)s, undefined field '%(hf)s' found while importing move lines"
                    )
                    % {"name": self._name, "hf": hf}
                )
                wiz_dict["skip_fields"].append(hf)
                continue

            orm_field = False
            field_def = wiz_dict["orm_fields"].get(hf)
            if not field_def:
                for f in wiz_dict["orm_fields"]:
                    if wiz_dict["orm_fields"][f]["string"].lower() == hf:
                        orm_field = f
                        field_def = wiz_dict["orm_fields"].get(f)
                        break
            else:
                orm_field = hf
            field_type = field_def["type"]

            try:
                ft = _FIELD_TYPE_MAP.get(field_type, field_type)
                wiz_dict["field_methods"][hf] = {
                    "method": getattr(self, "_handle_orm_%s" % ft),
                    "orm_field": orm_field,
                    "field_type": ft,
                }
            except AttributeError:
                _logger.error(
                    _(
                        "%(name)s, field '%(hf)s', "
                        "the import of ORM fields of type '%(type)s' "
                        "is not supported"
                    )
                    % {
                        "name": self._name,
                        "hf": hf,
                        "type": field_type,
                    }
                )
                wiz_dict["skip_fields"].append(hf)

        return header_fields

    def _log_line_error(self, wiz_dict, line, msg):
        if not line.get("log_line_error"):
            data = " | ".join(["%s" % line[hf] for hf in wiz_dict["header_fields"]])
            wiz_dict["err_log"] += (
                _("Error when processing line '%s'") % data + ":\n" + msg + "\n\n"
            )
            # Add flag to avoid reporting two times the same line.
            # This could happen for errors detected by
            # _read_xls as well as _proces_%
            line["log_line_error"] = True

    def _handle_orm_char(self, wiz_dict, field, line, move, aml_vals, orm_field=False):
        orm_field = orm_field or field
        if not aml_vals.get(orm_field):
            aml_vals[orm_field] = line[field]

    def _handle_orm_integer(
        self, wiz_dict, field, line, move, aml_vals, orm_field=False
    ):
        orm_field = orm_field or field
        if not aml_vals.get(orm_field):
            val = line[field]
            if val:
                if isinstance(val, str):
                    val = str2int(val.strip(), self.decimal_separator)
                elif isinstance(val, (float, bool)):
                    is_int = val % 1 == 0.0
                    if is_int:
                        val = int(val)
                    else:
                        val = False
                if val is False:
                    msg = _(
                        "Incorrect value '%(val)s' for field '%(field)s' of type Integer !"
                    ) % {
                        "val": line[field],
                        "field": field,
                    }
                    self._log_line_error(wiz_dict, line, msg)
                else:
                    aml_vals[orm_field] = val

    def _handle_orm_float(self, wiz_dict, field, line, move, aml_vals, orm_field=False):
        orm_field = orm_field or field
        if not aml_vals.get(orm_field):
            val = line[field]
            if val:
                if isinstance(val, str):
                    val = str2float(val.strip(), self.decimal_separator)
                elif isinstance(val, bool):
                    val = float(val)
                if val is False:
                    msg = _(
                        "Incorrect value '%(val)s' for field '%(field)s' of type Numeric !"
                    ) % {
                        "val": line[field],
                        "field": field,
                    }
                    self._log_line_error(wiz_dict, line, msg)
                else:
                    aml_vals[orm_field] = val

    def _handle_orm_boolean(
        self, wiz_dict, field, line, move, aml_vals, orm_field=False
    ):
        orm_field = orm_field or field
        if not aml_vals.get(orm_field):
            val = line[field]
            if isinstance(val, str):
                val = val.strip().capitalize()
                if val in ["", "0", "False"]:
                    val = False
                elif val in ["1", "True"]:
                    val = True
                if isinstance(val, str):
                    msg = _(
                        "Incorrect value '%(val)s' for field '%(field)s' of type Boolean !"
                    ) % {
                        "val": line[field],
                        "field": field,
                    }
                    self._log_line_error(wiz_dict, line, msg)
            aml_vals[orm_field] = val

    def _handle_orm_many2one(
        self, wiz_dict, field, line, move, aml_vals, orm_field=False
    ):
        orm_field = orm_field or field
        if not aml_vals.get(orm_field):
            val = line[field]
            if val:
                if isinstance(val, str):
                    model = self.env[wiz_dict["orm_fields"][orm_field]["relation"]]
                    recs = model.search([(model._rec_name, "=", val)])
                    if not recs:
                        msg = _("%(name)s '%(val)s' not found !") % {
                            "name": model._name,
                            "val": val,
                        }
                        self._log_line_error(wiz_dict, line, msg)
                        return
                    elif len(recs) > 1:
                        msg = _(
                            "Multiple records of type '%(name)s' with "
                            "field %(field)s '%(val)s' found !"
                        ) % {"name": model._name, "field": model._rec_name, "val": val}
                        self._log_line_error(wiz_dict, line, msg)
                        return
                    else:
                        aml_vals[orm_field] = recs.id
                else:
                    aml_vals[orm_field] = val

    def _handle_account(self, wiz_dict, field, line, move, aml_vals):
        if not aml_vals.get("account_id"):
            code = line[field]
            if code in wiz_dict["accounts_dict"]:
                aml_vals["account_id"] = wiz_dict["accounts_dict"][code]
            else:
                msg = _("Account with code '%s' not found !") % code
                self._log_line_error(wiz_dict, line, msg)

    def _handle_debit(self, wiz_dict, field, line, move, aml_vals):
        if "debit" not in aml_vals:
            debit = line[field]
            if isinstance(debit, str):
                debit = str2float(debit, self.decimal_separator)
            aml_vals["debit"] = debit

    def _handle_credit(self, wiz_dict, field, line, move, aml_vals):
        if "credit" not in aml_vals:
            credit = line[field]
            if isinstance(credit, str):
                credit = str2float(credit, self.decimal_separator)
            aml_vals["credit"] = credit

    def _handle_partner(self, wiz_dict, field, line, move, aml_vals):
        if not aml_vals.get("partner_id"):
            input_val = line[field]
            part_mod = self.env["res.partner"]
            dom = ["|", ("parent_id", "=", False), ("is_company", "=", True)]
            dom_ref = dom + [("ref", "=", input_val)]
            partners = part_mod.search(dom_ref)
            if not partners:
                dom_name = dom + [("name", "=", input_val)]
                partners = part_mod.search(dom_name)
            if not partners:
                msg = _("Partner '%s' not found !") % input_val
                self._log_line_error(wiz_dict, line, msg)
                return
            elif len(partners) > 1:
                msg = (
                    _("Multiple partners with Reference or Name '%s' found !")
                    % input_val
                )
                self._log_line_error(wiz_dict, line, msg)
                return
            else:
                partner = partners[0]
                aml_vals["partner_id"] = partner.id

    def _handle_product(self, wiz_dict, field, line, move, aml_vals):
        if not aml_vals.get("product_id"):
            input_val = line[field]
            prod_mod = self.env["product.product"]
            products = prod_mod.search([("default_code", "=", input_val)])
            if not products:
                products = prod_mod.search([("name", "=", input_val)])
            if not products:
                msg = _("Product '%s' not found !") % input_val
                self._log_line_error(wiz_dict, line, msg)
                return
            elif len(products) > 1:
                msg = (
                    _(
                        "Multiple products with Internal Reference "
                        "or Name '%s' found !"
                    )
                    % input_val
                )
                self._log_line_error(wiz_dict, line, msg)
                return
            else:
                product = products[0]
                aml_vals["product_id"] = product.id

    def _handle_date_maturity(self, wiz_dict, field, line, move, aml_vals):
        if not aml_vals.get("date_maturity"):
            due = line[field]
            try:
                datetime.strptime(due, "%Y-%m-%d")
                aml_vals["date_maturity"] = due
            except Exception:
                msg = _(
                    "Incorrect data format for field '%(field)s' "
                    "with value '%(due)s', "
                    " should be YYYY-MM-DD"
                ) % {"field": field, "due": due}
                self._log_line_error(wiz_dict, line, msg)

    def _handle_currency(self, wiz_dict, field, line, move, aml_vals):
        if not aml_vals.get("currency_id"):
            name = line[field]
            curr = self.env["res.currency"].search([("name", "=ilike", name)])
            if curr:
                aml_vals["currency_id"] = curr[0].id
            else:
                msg = _("Currency '%s' not found !") % name
                self._log_line_error(wiz_dict, line, msg)

    def _handle_analytic_account(self, wiz_dict, field, line, move, aml_vals):
        if not aml_vals.get("analytic_account_id"):
            ana_mod = self.env["account.analytic.account"]
            input_val = line[field]
            domain = [
                "|",
                ("company_id", "=", False),
                ("company_id", "=", move.company_id.id),
            ]
            analytic_accounts = ana_mod.search(domain + [("code", "=", input_val)])
            if len(analytic_accounts) == 1:
                aml_vals["analytic_account_id"] = analytic_accounts.id
            else:
                analytic_accounts = ana_mod.search(domain + [("name", "=", input_val)])
                if len(analytic_accounts) == 1:
                    aml_vals["analytic_account_id"] = analytic_accounts.id
            if not analytic_accounts:
                msg = _("Invalid Analytic Account '%s' !") % input_val
                self._log_line_error(wiz_dict, line, msg)
            elif len(analytic_accounts) > 1:
                msg = (
                    _("Multiple Analytic Accounts found that match with '%s' !") % input
                )
                self._log_line_error(wiz_dict, line, msg)

    def _handle_tax_grids(self, wiz_dict, field, line, move, aml_vals):
        if not aml_vals.get("tax_tag_ids"):
            tag_list = line[field].split(",")
            tags = self.env["account.account.tag"]
            for tag_name in tag_list:
                tag = tags.search(
                    [
                        ("name", "=", tag_name.strip()),
                        ("applicability", "=", "taxes"),
                        ("country_id", "=", move.company_id.country_id.id),
                    ]
                )
                if len(tag) == 1:
                    tags |= tag
                else:
                    msg = _("Tax Grid '%s' not found !") % tag_name
                    self._log_line_error(wiz_dict, line, msg)
            if tags:
                aml_vals["tax_tag_ids"] = [(6, 0, tags.ids)]

    def _process_line_vals(self, wiz_dict, line, move, aml_vals):
        """
        Use this method if you want to check/modify the
        line input values dict before calling the move write() method
        """
        self._process_line_vals_currency(wiz_dict, line, move, aml_vals)

        if "name" not in aml_vals:
            aml_vals["name"] = "/"

        if "debit" not in aml_vals:
            aml_vals["debit"] = 0.0

        if "credit" not in aml_vals:
            aml_vals["credit"] = 0.0

        if (
            aml_vals["debit"] < 0
            or aml_vals["credit"] < 0
            or aml_vals["debit"] * aml_vals["credit"] != 0
        ):
            msg = _("Incorrect debit/credit values !")
            self._log_line_error(wiz_dict, line, msg)

        if "partner_id" not in aml_vals:
            # required since otherwise the partner_id
            # of the previous entry is added
            aml_vals["partner_id"] = False

        all_fields = wiz_dict["field_methods"]
        required_fields = [x for x in all_fields if all_fields[x].get("required")]
        for rf in required_fields:
            if rf not in aml_vals:
                msg = (
                    _(
                        "The '%s' field is a required field "
                        "that must be correctly set."
                    )
                    % rf
                )
                self._log_line_error(wiz_dict, line, msg)

    def _process_line_vals_currency(self, wiz_dict, line, move, aml_vals):
        if "currency_id" in aml_vals:
            amt_cur = aml_vals.get("amount_currency", 0.0)
            debit = aml_vals.get("debit", 0.0)
            credit = aml_vals.get("credit", 0.0)
            cur = self.env["res.currency"].browse(aml_vals["currency_id"])
            company = move.company_id
            comp_cur = company.currency_id

            if (debit or credit) and not amt_cur:
                amt = debit or -credit
                aml_vals["amount_currency"] = comp_cur._convert(
                    amt, cur, company, move.date
                )

            elif amt_cur and not (debit or credit):
                amt = cur._convert(amt_cur, comp_cur, company, move.date)
                if amt > 0:
                    aml_vals["debit"] = amt
                else:
                    aml_vals["credit"] = -amt

    def _process_vals(self, wiz_dict, move, vals):
        """
        Use this method if you want to check/modify the
        input values dict before calling the move write() method
        """
        sum_debit = sum(x[2]["debit"] for x in vals)
        sum_credit = sum(x[2]["credit"] for x in vals)
        if not move.currency_id.is_zero(sum_debit - sum_credit):
            wiz_dict["err_log"] += (
                "\n"
                + _(
                    "Error in input file, Total Debit (%(sum_debit)s) is "
                    "different from Total Credit (%(sum_credit)s) !"
                )
                % {"sum_debit": sum_debit, "sum_credit": sum_credit}
                + "\n"
            )
        return vals
