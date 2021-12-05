# Copyright 2009-2021 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    transaction_numbering = fields.Selection(
        selection="_selection_transaction_numbering", default="journal"
    )

    @api.model
    def _selection_transaction_numbering(self):
        return [("journal", _("Journal Sequence")), ("statement", _("Statement Name"))]

    @api.onchange("type")
    def _onchange_type(self):
        super()._onchange_type()
        for rec in self:
            if rec.type != "bank":
                rec.transaction_numbering = "journal"
