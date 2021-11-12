# Copyright 2009-2021 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AccountPaymentLineCreate(models.TransientModel):
    _inherit = "account.payment.line.create"

    def _prepare_move_line_domain(self):
        """
        Temporary fix while waiting on merge of
        https://github.com/OCA/bank-payment/pull/656
        """
        ctx = dict(
            self.env.context,
            account_payment_order_fixes=True,
            company_id=self.order_id.company_id.id,
        )
        self = self.with_context(ctx)
        return super()._prepare_move_line_domain()
