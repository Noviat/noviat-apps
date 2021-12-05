# Copyright 2009-2021 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountBankStatement(models.Model):
    _inherit = "account.bank.statement"

    transaction_numbering = fields.Selection(related="journal_id.transaction_numbering")

    @api.model_create_multi
    def create(self, vals_list):
        # resequence to cover data entry without use of handle widget
        for vals in vals_list:
            seqs = [x[2]["sequence"] for x in vals.get("line_ids", [])]
            if len(seqs) != len(set(seqs)):
                vals["line_ids"].sort(key=lambda x: (x[2]["sequence"], x[1]))
                for i, line_vals in enumerate(vals["line_ids"], start=1):
                    line_vals[2]["sequence"] = i
        return super().create(vals_list)

    def write(self, vals):
        new_name = vals.get("name")
        for rec in self:
            rename = False
            if (
                rec.state == "open"
                and rec.transaction_numbering == "statement"
                and new_name
                and new_name != rec.name
            ):
                rename = True
            super(AccountBankStatement, rec).write(vals)
            if rename:
                for st_line in rec.line_ids:
                    st_line.name = "{}/{}".format(
                        new_name, str(st_line.sequence).rjust(3, "0")
                    )
        return True
