# Copyright 2009-2024 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, api, fields, models

from odoo.addons.account_bank_statement_advanced.models.account_bank_statement import (
    READONLY_IMPORT_FORMATS,
)


class AccountBankStatement(models.Model):
    _inherit = "account.bank.statement"

    transaction_numbering = fields.Selection(related="journal_id.transaction_numbering")

    @api.model_create_multi
    def create(self, vals_list):
        """
        We limit this logic to manual statement encoding in the statement form
        of the account_bank_statement_advanced module
        """
        if not self.env.context.get("absa") or len(vals_list) != 1:
            return super(AccountBankStatement, self).create(vals_list)

        vals_list_st_numbering = []
        vals_list_j_numbering = []

        # resequence to cover data entry without use of handle widget
        for vals in vals_list:

            if vals.get("import_format") in READONLY_IMPORT_FORMATS or not vals.get(
                "line_ids"
            ):
                continue

            statement_numbering = False
            journal_id = vals.get("journal_id")
            if not journal_id and vals["line_ids"]:
                journal_id = vals["line_ids"][0][2]["journal_id"]
                journal = self.env["account.journal"].browse(journal_id)
                if journal.transaction_numbering == "statement":
                    statement_numbering = True

            seqs = [x[2]["sequence"] for x in vals.get("line_ids", [])]
            if len(seqs) != len(set(seqs)):
                vals["line_ids"].sort(key=lambda x: (x[2]["sequence"], x[1]))
                for i, line_vals in enumerate(vals["line_ids"], start=1):
                    line_vals[2]["sequence"] = i

            if statement_numbering and vals.get("name"):
                for line_vals in vals["line_ids"]:
                    sequence = line_vals[2]["sequence"]
                    line_vals[2]["name"] = "{}/{}".format(
                        vals["name"], str(sequence).rjust(3, "0")
                    )

            if statement_numbering:
                vals_list_st_numbering.append(vals)
            else:
                vals_list_j_numbering.append(vals)

        self_st_nbr = self.with_context(skip_account_move_compute_name=True)
        recs = super(AccountBankStatement, self_st_nbr).create(vals_list_st_numbering)
        recs += super().create(vals_list_j_numbering)
        return recs

    def write(self, vals):
        """
        We limit this logic to manual encoding in the statement form
        of the account_bank_statement_advanced module

        We need to set the st_line name to False in case of resequencing
        by handle widget before assigning it again to avoid uniqueness
        constraint errors.
        """
        if (
            not self.env.context.get("absa")
            or len(self) != 1
            or (vals.get("import_format") or self.import_format)
            in READONLY_IMPORT_FORMATS
        ):
            return super(AccountBankStatement, self).write(vals)

        for rec in self:
            if rec.journal_id.transaction_numbering != "statement":
                super(AccountBankStatement, rec).write(vals)
                continue

            rec = rec.with_context(skip_account_move_compute_name=True)
            new_name = vals.get("name")
            st_name = new_name or self.name

            resequence = vals.get("line_ids") and any(
                [
                    entry
                    for entry in vals["line_ids"]
                    if (
                        entry[0] in (Command.CREATE, Command.UPDATE)
                        and "sequence" in entry[2]
                        and "name" not in entry[2]
                    )
                ]
            )

            if resequence:
                for entry in vals["line_ids"]:
                    if (
                        entry[0] in (Command.CREATE, Command.UPDATE)
                        and "sequence" in entry[2]
                        and "name" not in entry[2]
                    ):
                        entry[2]["name"] = False
                    elif entry[0] == Command.LINK:
                        st_line = self.line_ids
                        entry[0] = Command.UPDATE
                        entry[2] = {"name": False}

            rename = False
            if rec.state == "draft" and new_name and new_name != rec.name:
                rename = True

            super(AccountBankStatement, rec).write(vals)

            # flush account.move, name fields before updating them to avoid
            # unique constraint error message
            rec.line_ids.mapped("move_id").flush_recordset(fnames=["name"])

            if rename or resequence:
                for st_line in rec.line_ids:
                    st_line_name = "{}/{}".format(
                        st_name, str(st_line.sequence).rjust(3, "0")
                    )
                    if st_line_name != st_line.name:
                        st_line.name = st_line_name
        return True
