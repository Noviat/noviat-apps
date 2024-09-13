# Copyright 2009-2023 Noviat.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import api, models


class BankRecWidget(models.Model):
    _inherit = "bank.rec.widget"

    @api.depends("st_line_id")
    def _compute_transaction_currency_id(self):
        """
        Replace (NO SUPER !) of this method to address a functional shortcomings
        of standard Odoo:

        The standard Odoo Enterprise reconcile widget breaks on the use case
        of a bank transaction whereby the company currency value is provided
        within the bank transaction.
        """
        for wizard in self:
            # standard code:
            # wizard.transaction_currency_id = (
            #     wizard.st_line_id.foreign_currency_id or wizard.journal_currency_id
            # )
            # replaced by:
            wizard.transaction_currency_id = (
                wizard.st_line_id.foreign_currency_id != wizard.company_currency_id
                and wizard.st_line_id.foreign_currency_id
                or wizard.journal_currency_id
            )
