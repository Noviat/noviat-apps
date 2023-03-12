# Copyright 2009-2023 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AccountPaymentLineCreate(models.TransientModel):
    _inherit = "account.payment.line.create"

    def _prepare_move_line_domain(self):
        """
        Temporary fix while waiting on merge of
        https://github.com/OCA/bank-payment/pull/656
        """
        self = self.with_context(
            account_payment_order_fixes=True, company_id=self.order_id.company_id.id
        )
        return super()._prepare_move_line_domain()
