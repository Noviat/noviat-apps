# Copyright 2009-2024 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, models
from odoo.exceptions import ValidationError


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    @api.constrains("name", "date")
    def _constrains_date_sequence(self):
        for rec in self:
            if rec.name and rec.journal_id.transaction_numbering == "statement":
                if rec.statement_id.name not in rec.name:
                    raise ValidationError(
                        _(
                            "The transaction Journal Entry Name doesn't correspond "
                            "to the transaction number scheme set for "
                            "the financial journal.\n"
                            "The Journal Entry name should match 'statement_name/seq'."
                        )
                    )

            else:
                rec.move_id._constrains_date_sequence()
