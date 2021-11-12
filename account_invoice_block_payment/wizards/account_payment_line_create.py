# Copyright 2009-2021 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AccountPaymentLineCreate(models.TransientModel):
    _inherit = "account.payment.line.create"

    def _prepare_move_line_domain(self):
        dom = super()._prepare_move_line_domain()
        dom.append(("move_id.block_payment", "=", False))
        return dom
