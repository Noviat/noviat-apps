# Copyright 2009-2023 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, models
from odoo.exceptions import ValidationError


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            statement_id = (
                vals.get("statement_id")
                or self.env.context.get("default_statement_id")
                or (
                    self.env.context.get("active_model") == "account.bank.statement"
                    and self.env.context["active_id"]
                )
            )
            if not vals.get("name") and statement_id:
                statement = self.env["account.bank.statement"].browse(statement_id)
                journal = statement.journal_id
                if journal.transaction_numbering == "statement":
                    vals["name"] = "{}/{}".format(
                        statement["name"], str(vals["sequence"]).rjust(3, "0")
                    )
        return super().create(vals_list)

    @api.constrains("name", "date")
    def _constrains_date_sequence(self):
        for rec in self:
            if rec.journal_id.transaction_numbering == "statement":
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
