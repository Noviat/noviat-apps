# Copyright 2009-2021 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_invoice_register_payment(self):
        """
        Raise an error message if no payment methods (journals) are available for the
        Register Payment button or action.
        """
        res = super().action_invoice_register_payment()
        if not self:
            return res
        pj_dom = [
            ("type", "in", ("bank", "cash")),
            ("company_id", "=", self[0].company_id.id),
        ]
        amount = sum(
            [
                x.amount_residual * (x.type in ("out_invoice", "in_refund") and 1 or -1)
                for x in self
            ]
        )
        if amount > 0:
            pj_dom.append(("payment_method_in", "=", True))
        else:
            pj_dom.append(("payment_method_out", "=", True))
        pay_journals = self.env["account.journal"].search(pj_dom)
        if not pay_journals:
            raise UserError(
                _(
                    "No Payment Method (Journal) available to register the payment."
                    "\nPayment reconciliation is performed by the Finance Department "
                    "via Bank Statement processing."
                )
            )
        return res
