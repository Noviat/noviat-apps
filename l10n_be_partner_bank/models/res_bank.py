# Copyright 2009-2023 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval

COUNTRY_CODES = ["BE"]


class ResBank(models.Model):
    _inherit = "res.bank"

    # TODO: move bic constraint to account_bank_statement_advanced
    _sql_constraints = [("unique_bic", "unique(bic)", "The BIC must be unique.")]

    bban_codes = fields.Char(string="BBAN Codes")
    bban_code_list = fields.Char(
        compute="_compute_bban_code_list", store=True, readonly=False
    )

    @api.depends("bban_codes")
    def _compute_bban_code_list(self):
        self_codes = self.filtered(lambda r: r.bban_codes)
        self_no_codes = self - self_codes
        self_no_codes.update({"bban_code_list": False})
        for rec in self_codes:
            err_msg = _(
                "Error in BBAN Codes for '{bank}', BIC: {bic}: Incorrect BBAN code range"
            ).format(bank=rec.name, bic=rec.bic or "")
            codes = rec.bban_codes.split(",")
            code_list = []
            for code in codes:
                code_parts = code.split("-")
                if len(code_parts) == 1:
                    code_list.append(code)
                elif len(code_parts) == 2:
                    if any([len(x) != 3 for x in code_parts]):
                        raise UserError(err_msg)
                    start = int(code_parts[0])
                    end = int(code_parts[1])
                    if start >= end:
                        raise UserError(err_msg)
                    for nbr in range(start, end + 1):
                        code_list.append(str(nbr).rjust(3, "0"))
                else:
                    raise UserError(err_msg)
                rec.bban_code_list = str(code_list)

    @api.constrains("bban_codes")
    def _check_bban_codes(self):
        pattern = r"^[0-9,-]*$"
        for rec in self.filtered(
            lambda r: r.bban_codes and r.country.code in COUNTRY_CODES
        ):
            if not re.match(pattern, rec.bban_codes):
                raise UserError(
                    _(
                        "Error in BBAN Codes for {bank}: this should be a list of 3-digit codes"
                    ).format(bank=rec.name)
                )

    @api.constrains("bban_code_list")
    def _check_bban_code_list(self):
        banks = self.env["res.bank"].search(
            [("country.code", "in", COUNTRY_CODES), ("bban_code_list", "!=", False)]
        )
        for rec in self.filtered(lambda r: r.bban_code_list):
            code_list = safe_eval(rec.bban_code_list)
            for code in code_list:
                for bank in banks - rec:
                    if code in safe_eval(bank.bban_code_list):
                        raise UserError(
                            _(
                                "Error in BBAN Codes for '{bank}', BIC: {bic}: "
                                "BBAN code already encoded on '{dup}', BIC:  {dup_bic}"
                            ).format(
                                bank=rec.name,
                                bic=rec.bic,
                                dup=bank.name,
                                dup_bic=bank.bic,
                            )
                        )

    # TODO: move normalise_bic logic to account_bank_statement_advanced
    @api.model_create_multi
    def create(self, vals_list):
        [self._normalise_bic(vals) for vals in vals_list if "bic" in vals]
        return super().create(vals_list)

    def write(self, vals):
        if vals.get("bic"):
            self._normalise_bic(vals)
        return super().write(vals)

    def _normalise_bic(self, vals):
        vals["bic"] = vals["bic"].replace(" ", "").upper()

    @api.model
    def _name_search(
        self, name, args=None, operator="ilike", limit=100, name_get_uid=None
    ):
        args = args or []
        if name and operator == "ilike":
            be_bban = len(name) == 3 and name.isdigit()
            if be_bban:
                domain = [("bban_code_list", "ilike", name)]
                return self._search(
                    domain + args, limit=limit, access_rights_uid=name_get_uid
                )
        return super()._name_search(
            name, args=args, operator=operator, limit=limit, name_get_uid=name_get_uid
        )

    @api.model
    def _bban2iban(self, country_code, bban):
        if country_code not in COUNTRY_CODES:
            raise UserError(
                _(
                    "'{bban}': bban conversion not supported for country '{cc}' !"
                ).format(bban=bban, cc=country_code)
            )
        ok = True
        nr = bban.replace("-", "").replace(" ", "")
        if not nr.isdigit():
            ok = False
        elif int(nr) < 0:
            ok = False
        elif len(nr) != 12:
            ok = False
        if not ok:
            raise UserError(_("'{bban}': Incorrect BBAN Number !").format(bban=bban))
        kk = calc_iban_checksum("BE", nr)
        return "BE" + kk + nr


def calc_iban_checksum(country, bban):
    bban += country + "00"
    base = ""
    for c in bban:
        if c.isdigit():
            base += c
        else:
            base += str(ord(c) - ord("A") + 10)
    kk = 98 - int(base) % 97
    return str(kk).rjust(2, "0")
