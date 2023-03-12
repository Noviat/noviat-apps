# Copyright 2009-2023 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    refund_journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Refund Journal",
        domain="[('type', '=', type)]",
        help="Select the default Journal for Refunds created via the Refund Button.",
    )
    refund_usage = fields.Selection(
        selection=[("refund", "Refunds"), ("regular", "Regular"), ("both", "Both")],
        default="both",
        required=True,
        help="Use this field to restrict the use of a Sale/Purchase "
        "to only refunds or only regular invoices.",
    )

    @api.onchange("refund_usage")
    def _onchange_refund_usage(self):
        if self.refund_usage == "refund":
            self.refund_sequence = True
        elif self.refund_usage == "regular":
            self.refund_sequence = False
