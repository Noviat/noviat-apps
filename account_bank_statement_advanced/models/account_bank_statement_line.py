# Copyright 2009-2021 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    # new fields
    statement_date = fields.Date(
        related="statement_id.date", string="Statement Date", readonly=True, store=True
    )
    transaction_date = fields.Date(
        string="Transaction Date",
        required=True,
        default=lambda self: self._default_transaction_date(),
    )
    val_date = fields.Date(string="Value Date")  # nl: valuta datum)
    journal_code = fields.Char(
        related="statement_id.journal_id.code",
        string="Journal Code",
        store=True,
        readonly=True,
    )
    globalisation_id = fields.Many2one(
        comodel_name="account.bank.statement.line.global",
        string="Globalisation ID",
        readonly=True,
        help="Code to identify transactions belonging to the same "
        "globalisation level within a batch payment",
    )
    globalisation_amount = fields.Monetary(
        related="globalisation_id.amount", string="Glob. Amount", readonly=True
    )
    counterparty_bic = fields.Char(
        string="Counterparty BIC", size=11, states={"confirm": [("readonly", True)]}
    )
    # we do not use the standard account_number field since this will lauch
    # the _find_or_create_bank_account method which may not always be the
    # desired behaviour (e.g. in case of factoring)
    counterparty_number = fields.Char(
        string="Counterparty Number", states={"confirm": [("readonly", True)]}
    )
    counterparty_currency = fields.Char(
        string="Counterparty Currency", size=3, states={"confirm": [("readonly", True)]}
    )
    payment_reference = fields.Char(
        string="Payment Reference",
        size=35,
        states={"confirm": [("readonly", True)]},
        help="Payment Reference. For SEPA (SCT or SDD) transactions, "
        "the EndToEndReference is recorded in this field.",
    )
    creditor_reference_type = fields.Char(
        # To DO : change field to selection list
        string="Creditor Reference Type",
        size=35,
        states={"confirm": [("readonly", True)]},
        help="Creditor Reference Type. For SEPA (SCT) transactions, "
        "the <CdtrRefInf> type is recorded in this field."
        "\nE.g. 'BBA' for belgian structured communication "
        "(Code 'SCOR', Issuer 'BBA'",
    )
    creditor_reference = fields.Char(
        string="Creditor Reference",
        size=35,  # cf. pain.001.001.003 type="Max35Text"
        states={"confirm": [("readonly", True)]},
        help="Creditor Reference. For SEPA (SCT) transactions, "
        "the <CdtrRefInf> reference is recorded in this field.",
    )
    move_state = fields.Selection(
        related="move_id.state", store=True, string="Journal Entry State"
    )
    # update existing fields
    state = fields.Selection(store=True, string="Statement State")

    @api.model
    def _default_transaction_date(self):
        return self.env.context.get("statement_date")

    @api.onchange("foreign_currency_id", "val_date", "transaction_date")
    def _onchange_foreign_currency_id(self):
        if (
            self.foreign_currency_id
            and self.foreign_currency_id != self.currency_id
            and not self.amount_currency
        ):
            self.amount_currency = self.currency_id._convert(
                self.amount,
                self.foreign_currency_id,
                self.company_id,
                self.val_date or self.transaction_date,
            )
        if not self.foreign_currency_id or self.foreign_currency_id == self.currency_id:
            self.amount_currency = 0.0

    @api.model
    def _prepare_counterpart_move_line_vals(self, counterpart_vals, move_line=None):
        """
        TODO:
        check and if required adapt standard method to ensure that
        currency conversion uses the val_date/transaction_date.
        """
        return super()._prepare_counterpart_move_line_vals(
            counterpart_vals, move_line=move_line
        )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            statement = self.env["account.bank.statement"].browse(vals["statement_id"])
            if not vals.get("transaction_date"):
                vals["transaction_date"] = statement.date
            if not vals.get("date"):
                vals["date"] = statement.accounting_date or statement.date
        return super().create(vals_list)

    def unlink(self):
        glines = self.mapped("globalisation_id")
        todelete = glines.filtered(
            lambda gline: all(
                [stl_id in self.ids for stl_id in gline.bank_statement_line_ids.ids]
            )
        )
        todelete.unlink()
        return super().unlink()

    def button_view_move(self):
        self.ensure_one()
        act_move = {
            "name": _("Journal Entry"),
            "view_type": "form",
            "view_mode": "form",
            "res_model": "account.move",
            "res_id": self.move_id.id,
            "view_id": self.env.ref("account.view_move_form").id,
            "context": self.env.context,
            "type": "ir.actions.act_window",
        }
        return act_move

    def manual_reconcile(self):
        modules = ["account_accountant", "account_reconciliation_widget"]
        for module in modules:
            check = self.env.ref(
                "{}.action_bank_reconcile".format(module), raise_if_not_found=False
            )
            if check:
                break
        if not check:
            raise UserError(
                _(
                    "Missing reconcile widget.\n"
                    "You should install one of the following modules:\n%s"
                )
                % modules
            )
        return {
            "type": "ir.actions.client",
            "tag": "bank_statement_reconciliation_view",
            "context": {
                "statement_line_ids": self.ids,
                "company_ids": self.mapped("company_id").ids,
            },
        }

    def automatic_reconcile(self):
        reconcile_note = ""
        statements = self.mapped("statement_id")
        for st in statements:
            st_lines = self.filtered(lambda r: r.statement_id == st)
            reconcile_note += st._automatic_reconcile(
                reconcile_note=reconcile_note, st_lines=st_lines
            )
        if reconcile_note:
            module = __name__.split("addons.")[1].split(".")[0]
            result_view = self.env.ref(
                "%s.bank_statement_automatic_reconcile_result_view_form" % module
            )
            return {
                "name": _("Automatic Reconcile remarks:"),
                "view_type": "form",
                "view_mode": "form",
                "res_model": "bank.statement.automatic.reconcile.result.view",
                "view_id": result_view.id,
                "target": "new",
                "context": dict(self.env.context, note=reconcile_note),
                "type": "ir.actions.act_window",
            }
        else:
            return True
