# Copyright 2009-2021 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.depends(lambda self: [self._sequence_field])
    def _compute_split_sequence(self):
        for rec in self:
            if not rec.name or rec.name == "/":
                rec.sequence_prefix = None
                rec.sequence_number = None
            else:
                super(AccountMove, rec)._compute_split_sequence()

    def _constrains_date_sequence(self):
        """
        Bypass constraint for account.move,name = "/".
        Not doing so makes the regex syntax too complex for the
        account.journal,sequence_override_regex field that becomes available
        on the User Interface (Journal Settings) via this module.
        """
        return super(
            AccountMove, self.filtered(lambda r: r.name != "/")
        )._constrains_date_sequence()

    def _get_starting_sequence(self):
        starting_sequence = super()._get_starting_sequence()
        journal = self.journal_id
        if journal.refund_sequence and self.move_type in ("out_refund", "in_refund"):
            starting_sequence = journal.refund_starting_sequence or starting_sequence
        else:
            starting_sequence = journal.starting_sequence or starting_sequence
        return starting_sequence

    @api.model
    def _deduce_sequence_number_reset(self, name):
        if not name:
            name = self._get_starting_sequence()
        return super()._deduce_sequence_number_reset(name)

    def _get_sequence_format_param(self, previous):

        if previous == "/":
            return "never"
        return super()._get_sequence_format_param(previous)
