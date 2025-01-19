# Copyright 2009-2024 Noviat
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    @api.depends("line_ids", "company_id")
    def _compute_available_journal_ids(self):
        res = super()._compute_available_journal_ids()
        for rec in self:
            if rec.payment_type == "inbound":
                rec.available_journal_ids = rec.available_journal_ids.filtered(
                    lambda aj: aj.payment_method_in
                )
            else:
                rec.available_journal_ids = rec.available_journal_ids.filtered(
                    lambda aj: aj.payment_method_out
                )
        return res
