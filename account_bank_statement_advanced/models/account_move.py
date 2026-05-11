# Copyright 2009-2024 Noviat.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import _, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

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

    def _search_default_journal(self):
        """
        We don't set a default journal when entering a bank statement manually since
        journal_id is a required field that must be set before creating transactions.
        """
        if self.env.context.get("absa"):
            return self.env["account.journal"]
        else:
            return super()._search_default_journal()
