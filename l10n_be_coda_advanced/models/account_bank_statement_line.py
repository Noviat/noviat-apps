# Copyright 2009-2023 Noviat.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    coda_transaction_dict = fields.Char(
        string="CODA transaction details",
        help="JSON dictionary with the results of the CODA parsing",
    )

    def button_close(self):
        """
        Via this button we trigger the refresh of the O2M line_ids tree in order
        to see the result of the 'AUTOMATIC RECONCILE' button called from within
        the transaction form view.
        The refresh is not triggered since the line_ids are readonly.
        """
        return {"type": "ir.actions.client", "tag": "soft_reload"}
