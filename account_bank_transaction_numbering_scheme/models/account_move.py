# Copyright 2009-2024 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _compute_name(self):
        """
        Skip name computation when its handled by statement create/write.
        """
        if not self.env.context.get("skip_account_move_compute_name"):
            return super()._compute_name()

    def _constrains_date_sequence(self):
        for rec in self:
            if rec.journal_id.transaction_numbering != "statement":
                return super(AccountMove, rec)._constrains_date_sequence()
