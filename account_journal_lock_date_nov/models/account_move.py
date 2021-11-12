# Copyright 2019-2021 Noviat.
# Code inspired by OCA account_journal_lock_date 11.0 module
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    def _check_fiscalyear_lock_date(self):
        res = super()._check_fiscalyear_lock_date()
        self._check_journal_lock_date()
        return res

    def _check_journal_lock_date(self):
        if self.env["account.journal"]._can_bypass_journal_lock_date():
            return
        for move in self.filtered(lambda move: move.state == "posted"):
            lock_date = move.journal_id.journal_lock_date
            if lock_date and move.date <= lock_date:
                raise UserError(
                    _(
                        "You cannot post/modify entries prior to and "
                        "inclusive of the journal lock date %s"
                    )
                    % lock_date
                )

    @api.depends(
        "date",
        "line_ids.debit",
        "line_ids.credit",
        "line_ids.tax_line_id",
        "line_ids.tax_ids",
        "line_ids.tag_ids",
    )
    def _compute_tax_lock_date_message(self):
        """
        This code fixes bug in standard Odoo.
        The tax_lock_date_message should not be displayed for outgoing invoices since
        the accounting date field is not relevant for customer invoices (the field is
        hidden on the UI and should be set to the invoice date when posting.)
        """
        for move in self:
            if move.type in ("out_invoice", "out_refund", "out_receipt"):
                move.tax_lock_date_message = False
            else:
                super(AccountMove, move)._compute_tax_lock_date_message()

    def post(self):
        """
        Second part of the tax_lock_date fix for outgoing moves.
        """
        super().post()
        for move in self:
            if move.type in ("out_invoice", "out_refund", "out_receipt"):
                move.date = move.invoice_date
