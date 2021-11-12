# Copyright 2009-2021 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    def process_reconciliation(
        self, counterpart_aml_dicts=None, payment_aml_rec=None, new_aml_dicts=None
    ):
        if not self.move_name:
            statement = self.statement_id
            journal = statement.journal_id
            if journal.transaction_numbering == "statement":
                self.move_name = "{}/{}".format(
                    statement["name"], str(self.sequence).rjust(3, "0")
                )
        return super().process_reconciliation(
            counterpart_aml_dicts=counterpart_aml_dicts,
            payment_aml_rec=payment_aml_rec,
            new_aml_dicts=new_aml_dicts,
        )
