# Copyright 2009-2021 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models

from odoo.addons.base.models.res_bank import sanitize_account_number


class AccountStatementImport(models.TransientModel):
    """
    Add support for local bank account numbers which are in several
    countries a subset of the IBAN.
    Some banks also add the currency at the end of the local account number.
    """

    _inherit = "account.statement.import"

    def _match_journal(self, account_number, currency):
        journal = self.env["account.journal"]
        sanitized_account_number = self._sanitize_account_number(account_number)
        fin_journals = self.env["account.journal"].search(
            [
                ("type", "=", "bank"),
                "|",
                ("currency_id", "=", currency.id),
                ("company_id.currency_id", "=", currency.id),
            ]
        )
        fin_journal = fin_journals.filtered(
            lambda r: sanitized_account_number
            in (r.bank_account_id.sanitized_acc_number or "")
        )
        if len(fin_journal) == 1:
            journal = fin_journal
        if not journal:
            journal = super()._match_journal(account_number, currency)
        return journal

    def _sanitize_account_number(self, account_number):
        sanitized_number = sanitize_account_number(account_number)
        check_curr = sanitized_number[-3:]
        if check_curr.isalpha():
            all_currencies = self.env["res.currency"].search([])
            if check_curr in all_currencies.mapped("name"):
                sanitized_number = sanitized_number[:-3]
        return sanitized_number
