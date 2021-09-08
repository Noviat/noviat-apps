# Copyright 2009-2020 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_starting_sequence(self):
        self.ensure_one()
        starting_sequence = super()._get_starting_sequence()
        journal = self.journal_id
        if journal.refund_sequence and self.move_type in ("out_refund", "in_refund"):
            starting_sequence = journal.refund_starting_sequence or starting_sequence
        else:
            starting_sequence = journal.starting_sequence or starting_sequence
        return starting_sequence
