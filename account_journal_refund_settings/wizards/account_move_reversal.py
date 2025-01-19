# Copyright 2009-2024 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class AccountMoveReversal(models.TransientModel):
    _inherit = "account.move.reversal"

    @api.depends("move_ids")
    def _compute_available_journal_ids(self):
        res = super()._compute_available_journal_ids()
        for record in self:
            am_in = record.move_ids and record.move_ids[0]
            if am_in and am_in.is_invoice():
                aj_in = am_in.journal_id
                aj_out_dom = [
                    ("type", "=", aj_in.type),
                    ("company_id", "=", record.company_id.id),
                ]
                if am_in.move_type in ["in_invoice", "out_invoice"]:
                    aj_out_dom.append(("refund_usage", "!=", "regular"))
                    record.available_journal_ids = self.env["account.journal"].search(
                        aj_out_dom
                    )
                else:
                    aj_out_dom.append(("refund_usage", "!=", "refund"))
                    record.available_journal_ids = self.env["account.journal"].search(
                        aj_out_dom
                    )
        return res

    @api.depends("move_ids")
    def _compute_journal_id(self):
        res = super()._compute_journal_id()
        for record in self:
            am_in = record.move_ids and record.move_ids[0]
            if am_in and am_in.is_invoice():
                aj_in = am_in.journal_id
                if aj_in.refund_journal_id:
                    record.journal_id = aj_in.refund_journal_id
        return res
