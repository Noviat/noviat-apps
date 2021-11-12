# Copyright 2009-2020 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class AccountMoveReversal(models.TransientModel):
    _inherit = "account.move.reversal"

    @api.onchange("move_type")
    def _onchange_move_id(self):
        am_in = self.move_id
        if am_in.is_invoice():
            aj_in = self.move_id.journal_id
            aj_out_dom = [("type", "=", aj_in.type)]
            if aj_in.refund_usage != "both":
                self.journal_id = aj_in.refund_journal_id
            if am_in.type in ["in_invoice", "out_invoice"]:
                aj_out_dom.append(("refund_usage", "!=", "regular"))
            else:
                aj_out_dom.append(("refund_usage", "!=", "refund"))
            return {"domain": {"journal_id": aj_out_dom}}

    def _prepare_default_reversal(self, move):
        res = super()._prepare_default_reversal(move)
        if move.is_invoice() and move.journal_id.refund_usage != "both":
            res["journal_id"] = move.journal_id.refund_journal_id.id
        return res
