# Copyright 2009-2021 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError

# mapping invoice type to journal type
_T2T = {
    "out_invoice": "sale",
    "in_invoice": "purchase",
    "out_refund": "sale",
    "in_refund": "purchase",
}
# mapping invoice type to journal refund_usage
_T2U = {
    "out_invoice": ["both", "regular"],
    "out_refund": ["both", "refund"],
    "in_invoice": ["both", "regular"],
    "in_refund": ["both", "refund"],
}


class AccountMove(models.Model):
    _inherit = "account.move"

    journal_id = fields.Many2one(default=lambda self: self._get_default_journal())

    @api.model
    def _get_default_journal(self):
        if self.env.context.get("default_journal_id"):
            return super()._get_default_journal()
        inv_type = self.env.context.get("default_type")
        if inv_type not in ("out_invoice", "in_invoice", "out_refund", "in_refund"):
            return super()._get_default_journal()
        j_type = _T2T.get(inv_type)
        j_refund_usage = _T2U.get(inv_type)
        if j_type and j_refund_usage:
            company_id = self._context.get(
                "force_company",
                self.env.context.get("default_company_id", self.env.company.id),
            )
            j_dom = [
                ("type", "=", j_type),
                ("refund_usage", "in", j_refund_usage),
                ("company_id", "=", company_id),
            ]
            journals = self.env["account.journal"].search(j_dom)
            if len(journals) == 1:
                return journals
            else:
                if not self.env.context.get("active_model"):
                    # return empty journal to enforce manual selection
                    return self.env["account.journal"]
                elif self.env.context.get("active_model") == "sale.order":
                    journals = self._guess_sale_order_journals(journals)
                    if len(journals) == 1:
                        return journals
        return super()._get_default_journal()

    def _guess_sale_order_journals(self, journals):
        """
        You can use this method to add your own logic when
        there are multiple sale journals.
        As an alternative we suggest to inherit the sale.order object and
        use customer specific logic to select the appropriate
        sales journal and add this one to the context via the
        'default_journal_id' key.

        The code below covers the case where the POS is installed
        and configured with a seperate sales journal for the POS orders.
        """
        if "pos.config" in self.env:
            pos_configs = self.env["pos.config"].sudo().search([])
            for pos_config in pos_configs:
                if pos_config.journal_id != pos_config.invoice_journal_id:
                    journals -= pos_config.journal_id
        return journals

    @api.onchange("type")
    def _onchange_type(self):
        res = super()._onchange_type() or {"domain": {}}
        company_id = self.env.context.get(
            "force_company",
            self.env.context.get("default_company_id", self.env.company.id),
        )
        # set company to avoid stack trace when entering lines with empty journal
        self.company_id = self.env["res.company"].browse(company_id)
        j_dom = [
            ("type", "=?", self.invoice_filter_type_domain),
            ("company_id", "=", company_id),
        ]
        if self.is_invoice() and self.journal_id.refund_usage != "both":
            if self.type in ["in_invoice", "out_invoice"]:
                j_dom.append(("refund_usage", "!=", "refund"))
            else:
                j_dom.append(("refund_usage", "!=", "regular"))
        res["domain"]["journal_id"] = j_dom
        return res

    @api.onchange("journal_id")
    def _onchange_journal(self):
        super()._onchange_journal()
        if not self.currency_id:
            self.currency_id = (
                self.journal_id.currency_id or self.env.company.currency_id
            )
            self._onchange_currency()

    def _reverse_move_vals(self, default_values, cancel=True):
        vals = super()._reverse_move_vals(default_values, cancel=cancel)
        if self.is_invoice() and self.journal_id.refund_usage != "both":
            vals["journal_id"] = (
                self.journal_id.refund_journal_id.id or vals["journal_id"]
            )
        return vals

    def action_switch_invoice_into_refund_credit_note(self):
        super().action_switch_invoice_into_refund_credit_note()
        for move in self:
            if (
                move.is_invoice()
                and move.journal_id.refund_usage != "both"
                and move.journal_id.refund_journal_id
            ):
                move.journal_id = move.journal_id.refund_journal_id

    def post(self):
        for move in self:
            if move.is_invoice() and move.journal_id.refund_usage != "both":
                if move.journal_id.refund_usage == "regular" and move.type in (
                    "in_refund",
                    "out_refund",
                ):
                    raise UserError(
                        _(
                            "You cannot post a refund in a "
                            "regular sale/purchase journal."
                        )
                    )
                elif move.journal_id.refund_usage == "refund" and move.type in (
                    "in_invoice",
                    "out_invoice",
                ):
                    raise UserError(
                        _(
                            "You cannot post a regular invoice in a "
                            "dedicated refund journal."
                        )
                    )
        super().post()


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.onchange("product_uom_id")
    def _onchange_uom_id(self):
        if not self.move_id.journal_id:
            raise UserError(_("Select the Journal before entering lines."))
        return super()._onchange_uom_id()
