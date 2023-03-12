# Copyright 2009-2023 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    starting_sequence = fields.Char()
    refund_starting_sequence = fields.Char()

    @api.onchange("refund_sequence")
    def _onchange_refund_sequence(self):
        """
        logic based upon account_move, _get_starting_sequence method.
        """
        today = fields.Date.context_today(self)
        self.starting_sequence = "%s/%04d/%02d/0000" % (
            self.code,
            today.year,
            today.month,
        )
        if self.refund_sequence:
            self.refund_starting_sequence = "R" + self.starting_sequence
        else:
            self.refund_starting_sequence = self.starting_sequence

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            strip_starting_sequence(vals)
        return super().create(vals_list)

    def write(self, vals):
        strip_starting_sequence(vals)
        return super().write(vals)


def strip_starting_sequence(vals):
    for fld in vals:
        if fld == "sequence_override_regex" and vals[fld]:
            vals[fld] = vals[fld].strip()
