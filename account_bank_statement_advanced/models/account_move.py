# Copyright 2009-2023 Noviat.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    date = fields.Date(default=lambda self: self._default_date())

    @api.model
    def _default_date(self):
        return (
            self.env.context.get("accounting_date")
            or self.env.context.get("statement_date")
            or fields.Date.context_today(self)
        )

    def button_draft(self):
        for move in self:
            for move_line in move.line_ids:
                st = move_line.statement_id
                if st and st.state == "confirm":
                    raise UserError(
                        _(
                            "Operation not allowed ! "
                            "\nYou cannot unpost an Accounting Entry "
                            "that is linked to a Validated Bank Statement."
                        )
                    )
        return super().button_draft()

    def button_cancel(self):
        for move in self:
            for move_line in move.line_ids:
                st = move_line.statement_id
                if st and st.state == "confirm":
                    raise UserError(
                        _(
                            "Operation not allowed ! "
                            "\nYou cannot cancel an Accounting Entry "
                            "that is linked to a Validated Bank Statement."
                        )
                    )
        return super().button_cancel()
