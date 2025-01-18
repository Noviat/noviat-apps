# Copyright 2009-2020 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    coda_transaction_dict = fields.Char(
        string="CODA transaction details",
        help="JSON dictionary with the results of the CODA parsing",
    )

    def _prepare_move_line_for_currency(self, aml_dict, date):
        date = self.val_date or date
        exchange_diff_aml = aml_dict.pop("exchange_diff_aml", False)
        if not exchange_diff_aml:
            super()._prepare_move_line_for_currency(aml_dict, date)
