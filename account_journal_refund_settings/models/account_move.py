# Copyright 2009-2024 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, models
from odoo.exceptions import UserError

# mapping invoice type to journal type
T2T = {
    "out_invoice": "sale",
    "in_invoice": "purchase",
    "out_refund": "sale",
    "in_refund": "purchase",
}
# mapping invoice type to journal refund_usage
T2U = {
    "out_invoice": ["both", "regular"],
    "out_refund": ["both", "refund"],
    "in_invoice": ["both", "regular"],
    "in_refund": ["both", "refund"],
}


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.depends("company_id", "invoice_filter_type_domain")
    def _compute_suitable_journal_ids(self):
        res = super()._compute_suitable_journal_ids()
        for move in self:
            j_type = T2T.get(move.move_type)
            j_refund_usage = T2U.get(move.move_type)
            if j_type and j_refund_usage:
                company_id = (self.company_id or self.env.company).id
                j_dom = [
                    ("type", "=", j_type),
                    ("refund_usage", "in", j_refund_usage),
                    ("company_id", "=", company_id),
                ]
                move.suitable_journal_ids = self.env["account.journal"].search(j_dom)
        return res

    def action_switch_invoice_into_refund_credit_note(self):
        super().action_switch_invoice_into_refund_credit_note()
        for move in self:
            if (
                move.is_invoice()
                and move.journal_id.refund_usage != "both"
                and move.journal_id.refund_journal_id
            ):
                move.journal_id = move.journal_id.refund_journal_id
        return

    def action_post(self):
        for move in self:
            if move.is_invoice() and move.journal_id.refund_usage != "both":
                if move.journal_id.refund_usage == "regular" and move.move_type in (
                    "in_refund",
                    "out_refund",
                ):
                    raise UserError(
                        _(
                            "You cannot post a refund in a "
                            "regular sale/purchase journal."
                        )
                    )
                elif move.journal_id.refund_usage == "refund" and move.move_type in (
                    "in_invoice",
                    "out_invoice",
                ):
                    raise UserError(
                        _(
                            "You cannot post a regular invoice in a "
                            "dedicated refund journal."
                        )
                    )
        return super().action_post()

    def _search_default_journal(self):
        journal = super()._search_default_journal()
        j_type = T2T.get(self.move_type)
        j_refund_usage = T2U.get(self.move_type)
        if j_type and j_refund_usage:
            company_id = (self.company_id or self.env.company).id
            j_dom = [
                ("type", "=", j_type),
                ("refund_usage", "in", j_refund_usage),
                ("company_id", "=", company_id),
            ]
            journals = self.env["account.journal"].search(j_dom)
            if len(journals) == 1:
                journal = journals
        return journal
