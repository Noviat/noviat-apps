# Copyright 2009-2021 Noviat.
# License LGPL-3 or later (http://www.gnu.org/licenses/lpgl).

from odoo import models

from odoo.addons.base.models.res_bank import sanitize_account_number


class AccountBankStatementImport(models.TransientModel):
    """
    Add support for local bank account numbers which are in several
    countries a subset of the IBAN.
    Some banks also add the currency at the end of the local account number.
    """

    _inherit = "account.bank.statement.import"

    def _find_additional_data(self, currency_code, account_number):
        currency, journal = super()._find_additional_data(currency_code, account_number)
        if not journal:
            sanitized_account_number = self._sanitize_account_number(account_number)
            fin_journals = self.env["account.journal"].search([("type", "=", "bank")])
            fin_journal = fin_journals.filtered(
                lambda r: sanitized_account_number
                in (r.bank_account_id.sanitized_acc_number or "")
            )
            if len(fin_journal) == 1:
                journal = fin_journal
        return currency, journal

    def _check_journal_bank_account(self, journal, account_number):
        check = super()._check_journal_bank_account(journal, account_number)
        if not check:
            number = self._sanitize_account_number(account_number)
            check = number in journal.bank_account_id.sanitized_acc_number
        return check

    def _sanitize_account_number(self, account_number):
        sanitized_number = sanitize_account_number(account_number)
        check_curr = sanitized_number[-3:]
        if check_curr.isalpha():
            all_currencies = self.env["res.currency"].search([])
            if check_curr in all_currencies.mapped("name"):
                sanitized_number = sanitized_number[:-3]
        return sanitized_number
