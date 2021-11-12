# Copyright 2009-2021 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import _, models

_logger = logging.getLogger(__name__)


class AccountBankStatementLineXlsx(models.AbstractModel):
    _name = "report.account_bank_statement_line_xlsx"
    _inherit = "report.report_xlsx.abstract"
    _description = "Bank Transactions XLSX export"

    def _get_ws_params(self, workbook, data, amls):

        # XLSX Template
        col_specs = {
            "j_code": {
                "header": {"value": _("Journal")},
                "lines": {"value": self._render("line.statement_id.journal_id.code")},
                "width": 10,
            },
            "date": {
                "header": {"value": _("Date")},
                "lines": {
                    "value": self._render("line.val_date or line.date"),
                    "format": self.format_tcell_date_left,
                },
                "width": 13,
            },
            "statement": {
                "header": {"value": _("Statement")},
                "lines": {"value": self._render("line.statement_id.name")},
                "width": 15,
            },
            "partner": {
                "header": {"value": _("Partner")},
                "lines": {
                    "value": self._render(
                        "line.partner_id and line.partner_id.name or ''"
                    )
                },
                "width": 36,
            },
            "communication": {
                "header": {"value": _("Communication")},
                "lines": {"value": self._render("line.name")},
                "width": 40,
            },
            "amount": {
                "header": {
                    "value": _("Amount"),
                    "format": self.format_theader_yellow_right,
                },
                "lines": {
                    "value": self._render("line.amount"),
                    "format": self.format_tcell_amount_right,
                },
                "totals": {
                    "type": "formula",
                    "value": self._render("amount_formula"),
                    "format": self.format_theader_yellow_amount_right,
                },
                "width": 18,
            },
        }
        wanted_list = [x for x in col_specs]
        title = _("Bank Transactions")

        return [
            {
                "ws_name": title,
                "generate_ws_method": "_absl_export",
                "title": title,
                "wanted_list": wanted_list,
                "col_specs": col_specs,
            }
        ]

    def _absl_export(self, workbook, ws, ws_params, data, lines):

        ws.set_landscape()
        ws.fit_to_pages(1, 0)
        ws.set_header(self.xls_headers["standard"])
        ws.set_footer(self.xls_footers["standard"])

        self._set_column_width(ws, ws_params)

        row_pos = 0
        row_pos = self._write_ws_title(ws, row_pos, ws_params)

        row_pos = self._write_line(
            ws,
            row_pos,
            ws_params,
            col_specs_section="header",
            default_format=self.format_theader_yellow_left,
        )

        ws.freeze_panes(row_pos, 0)

        wanted_list = ws_params["wanted_list"]
        amount_pos = "amount" in wanted_list and wanted_list.index("amount")

        for line in lines:
            row_pos = self._write_line(
                ws,
                row_pos,
                ws_params,
                col_specs_section="lines",
                render_space={"line": line},
                default_format=self.format_tcell_left,
            )

        line_cnt = len(lines)
        amount_start = self._rowcol_to_cell(row_pos - line_cnt, amount_pos)
        amount_stop = self._rowcol_to_cell(row_pos - 1, amount_pos)
        amount_formula = "SUM({}:{})".format(amount_start, amount_stop)
        row_pos = self._write_line(
            ws,
            row_pos,
            ws_params,
            col_specs_section="totals",
            render_space={"amount_formula": amount_formula},
            default_format=self.format_theader_yellow_left,
        )
