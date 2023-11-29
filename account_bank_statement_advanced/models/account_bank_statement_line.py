# Copyright 2009-2023 Noviat.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).


from xmlrpc.client import MAXINT

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.account.models.account_bank_statement_line import (
    AccountBankStatementLine as ABSL,
)

from .account_bank_statement import READONLY_IMPORT_FORMATS


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    import_format = fields.Char(related="statement_id.import_format")
    import_format_readonly = fields.Boolean(
        related="statement_id.import_format_readonly"
    )
    statement_date = fields.Date(
        related="statement_id.date", string="Statement Date", readonly=True, store=True
    )
    transaction_date = fields.Date(
        required=True,
    )
    val_date = fields.Date(string="Value Date")  # nl: valuta datum
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
    counterparty_bic = fields.Char(string="Counterparty BIC", size=11)
    # we do not use the standard account_number field since this will lauch
    # the _find_or_create_bank_account method which may not always be the
    # desired behaviour (e.g. in case of factoring)
    counterparty_number = fields.Char()
    counterparty_currency = fields.Char(size=3)
    payment_reference = fields.Char(
        size=35,
        help="Payment Reference. For SEPA (SCT or SDD) transactions, "
        "the EndToEndReference is recorded in this field.",
    )
    creditor_reference_type = fields.Char(
        # To DO : change field to selection list
        size=35,
        help="Creditor Reference Type. For SEPA (SCT) transactions, "
        "the <CdtrRefInf> type is recorded in this field."
        "\nE.g. 'BBA' for belgian structured communication "
        "(Code 'SCOR', Issuer 'BBA'",
    )
    creditor_reference = fields.Char(
        size=35,  # cf. pain.001.001.003 type="Max35Text"
        help="Creditor Reference. For SEPA (SCT) transactions, "
        "the <CdtrRefInf> reference is recorded in this field.",
    )
    statement_state = fields.Selection(
        related="statement_id.state",
        store=True,
        string="Statement State",
        readonly=True,
    )
    reconcile_state = fields.Selection(
        selection=[("reconciled", "Reconciled"), ("unreconciled", "Unreconciled")],
        compute="_compute_reconcile_state",
    )
    is_readonly = fields.Boolean(compute="_compute_is_readonly")

    @api.depends("transaction_date", "sequence")
    def _compute_internal_index(self):
        """
        Replace this method to work on transaction_date i.s.o. date.
        """
        for st_line in self.filtered(lambda line: line._origin.id):
            st_line.internal_index = (
                f'{st_line.transaction_date.strftime("%Y%m%d")}'
                f"{MAXINT - st_line.sequence:0>10}"
                f"{st_line._origin.id:0>10}"
            )

    @api.depends("is_reconciled")
    def _compute_reconcile_state(self):
        for rec in self:
            rec.reconcile_state = rec.is_reconciled and "reconciled" or "unreconciled"

    @api.depends("is_reconciled", "statement_state", "import_format_readonly")
    def _compute_is_readonly(self):
        for rec in self:
            rec.is_readonly = (
                rec.is_reconciled
                or rec.statement_state == "confirm"
                or rec.import_format_readonly
            )

    @api.onchange("transaction_date")
    def _onchange_transaction_date(self):
        self.date = self.statement_id.accounting_date or self.transaction_date

    @api.onchange("foreign_currency_id", "transaction_date")
    def _onchange_foreign_currency_id(self):
        if (
            self.foreign_currency_id
            and self.foreign_currency_id != self.currency_id
            and not self.amount_currency
        ):
            self.amount_currency = self.currency_id._convert(
                self.amount,
                self.foreign_currency_id,
                self.journal_id.company_id,
                self.transaction_date,
            )
        if not self.foreign_currency_id or self.foreign_currency_id == self.currency_id:
            self.amount_currency = 0.0

    def _get_amounts_with_currencies(self):
        """
        Replace (NO SUPER !) of this method to address two functional shortcomings
        of standard Odoo:

        1) Standard Odoo breaks on the use case of a bank transaction whereby
        the company currency value is provided within the bank transaction.

        2) Standard Odoo doesn't take into account the transaction date. This date can
        be different frome the accounting date (e.g. when encoding an old bank statement
        after period close.
        """
        self.ensure_one()

        company_currency = self.journal_id.company_id.currency_id
        journal_currency = self.journal_id.currency_id or company_currency
        foreign_currency = (
            self.foreign_currency_id or journal_currency or company_currency
        )

        journal_amount = self.amount
        transaction_amount = journal_amount
        if self.foreign_currency_id and self.foreign_currency_id not in (
            journal_currency,
            company_currency,
        ):
            transaction_amount = self.amount_currency

        if journal_currency == company_currency:
            company_amount = journal_amount
        elif self.foreign_currency_id == company_currency:
            company_amount = self.amount_currency
            foreign_currency = journal_currency
        else:
            company_amount = journal_currency._convert(
                journal_amount,
                company_currency,
                self.journal_id.company_id,
                self.transaction_date or self.date,
            )

        return (
            company_amount,
            company_currency,
            journal_amount,
            journal_currency,
            transaction_amount,
            foreign_currency,
        )

    def _synchronize_to_moves(self, changed_fields):
        """
        Replace (NO SUPER !) of this method to address a functional shortcoming

        Standard Odoo breaks on the use case of a bank transaction whereby
        the company currency value is provided within the bank transaction.
        """
        if self.env.context.get("skip_account_move_synchronization"):
            return

        if not any(
            field_name in changed_fields
            for field_name in (
                "payment_ref",
                "amount",
                "amount_currency",
                "foreign_currency_id",
                "currency_id",
                "partner_id",
            )
        ):
            return

        for st_line in self.with_context(skip_account_move_synchronization=True):
            liquidity_lines, suspense_lines, other_lines = st_line._seek_for_lines()
            journal = st_line.journal_id
            company_currency = journal.company_id.currency_id
            # journal_currency = (journal.currency_id
            #     if journal.currency_id != company_currency
            #     else False
            # )

            line_vals_list = st_line._prepare_move_line_default_vals()
            line_ids_commands = [(1, liquidity_lines.id, line_vals_list[0])]

            if suspense_lines:
                line_ids_commands.append((1, suspense_lines.id, line_vals_list[1]))
            else:
                line_ids_commands.append((0, 0, line_vals_list[1]))

            for line in other_lines:
                line_ids_commands.append((2, line.id))

            # replace st_line_vals['currenty_id'] logic
            # standard Odoo logic:
            # st_line.foreign_currency_id or journal_currency or company_currency
            if st_line.foreign_currency_id == company_currency:
                st_line_currency = journal.currency_id
            else:
                st_line_currency = (
                    st_line.foreign_currency_id
                    or journal.currency_id
                    or company_currency
                )
            st_line_vals = {
                "currency_id": st_line_currency.id,
                "line_ids": line_ids_commands,
            }
            if st_line.move_id.journal_id != journal:
                st_line_vals["journal_id"] = journal.id
            if st_line.move_id.partner_id != st_line.partner_id:
                st_line_vals["partner_id"] = st_line.partner_id.id
            st_line.move_id.write(st_line_vals)

    @api.model_create_multi
    def create(self, vals_list):
        vals_list_no_amount = []
        vals_list_skip_sync = []
        for vals in vals_list:
            statement_id = (
                vals.get("statement_id")
                or self.env.context.get("default_statement_id")
                or (
                    self.env.context.get("accive_model") == "account.bank.statement"
                    and self.env.context["active_id"]
                )
            )
            skip_sync = False
            if statement_id:
                statement = self.env["account.bank.statement"].browse(statement_id)
                vals["journal_id"] = statement.journal_id.id
                if not vals.get("transaction_date"):
                    vals["transaction_date"] = statement.date
                if not vals.get("date"):
                    vals["date"] = statement.accounting_date or statement.date
                if statement.import_format in READONLY_IMPORT_FORMATS:
                    skip_sync = True
            else:
                vals["transaction_date"] = vals["date"]
            if not vals.get("amount"):
                vals_list_no_amount.append(vals)
            elif skip_sync:
                vals_list_skip_sync.append(vals)

        # do not create amls when no amount (e.g. globalisation line)
        if vals_list_no_amount:
            absls_no_amount = super(ABSL, self).create(vals_list_no_amount)
            super(ABSL, absls_no_amount).write({"state": "posted"})
            for vals in vals_list_no_amount:
                vals_list.remove(vals)
        for vals in vals_list_skip_sync:
            vals_list.remove(vals)
        # _synchronize_from_moves doesn't make sense for transactions imported
        # from a reliable source such as camt053, cfonb120, coda
        self_no_sync = self.with_context(skip_account_move_synchronization=True)
        absls_skip_sync = super(AccountBankStatementLine, self_no_sync).create(
            vals_list_skip_sync
        )
        return absls_skip_sync + super().create(vals_list)

    def write(self, vals):
        lines = self.browse()
        for rec in self:
            if (
                vals.get("date")
                and not vals.get("transaction_date")
                and not rec.statement_id
                and rec.transaction_date.isoformat() != vals["date"]
            ):
                lines += rec
        if lines:
            super(AccountBankStatementLine, self - lines).write(vals)
            super(AccountBankStatementLine, lines).write(
                dict(vals, transaction_date=vals["date"])
            )
        else:
            super().write(vals)
        return True

    def unlink(self):
        glines = self.mapped("globalisation_id")
        todelete = glines.filtered(
            lambda gline: all(
                [stl_id in self.ids for stl_id in gline.bank_statement_line_ids.ids]
            )
        )
        todelete.unlink()
        return super().unlink()

    def view_transaction_details(self):
        act = self.env["ir.actions.actions"]._for_xml_id(
            "account_bank_statement_advanced.account_bank_statement_line_action"
        )
        act.update(
            {
                "res_id": self.id,
                "views": [x for x in act["views"] if x[1] == "form"],
                "target": "new",
            }
        )
        return act

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
        self.ensure_one()
        act_oe = "action_open_bank_reconcile_widget"
        if hasattr(self.statement_id, act_oe):
            action = getattr(self.statement_id, act_oe)()
            action["domain"] = [("id", "=", self.id)]
            return action
        elif "account.reconcile.abstract" in self.env:  # account_reconcile_oca
            act_name = "account_reconcile_oca.action_bank_statement_line_reconcile"
            action = self.env["ir.actions.actions"]._for_xml_id(act_name)
            action["domain"] = [("id", "=", self.id)]
            action["context"] = dict(
                self.env.context,
                view_ref="account_reconcile_oca.bank_statement_line_form_reconcile_view",
            )
            return action
        else:
            modules = ["account_accountant", "account_reconcile_oca"]
            raise UserError(
                _(
                    "Missing reconcile widget.\n"
                    "You should install one of the following modules:\n%s"
                )
                % modules
            )

    def automatic_reconcile(self):
        """
        This method is called by modules that implement automatic reconciliation
        via UI button, e.g. l10n_be_coda_advanced
        """
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

    def _reconcile(self, amls_vals):
        """
        Reconcile the bank transaction by creating Journal Items
        with the values provided by the amls_vals.

        :param amls_vals: a list of dictionaries containing the values for the
            creation of account.move.line records to balance the liquidity line.
            The following keys in such a dictionary result in extra processing:
            - balance : substitute for debit/credit
            - counterpart_aml_id : if given the newly created line will be reonciled
                 this account.move.line record
        """
        self.ensure_one()
        self.move_id.state = "draft"
        liquidity_aml = self.move_id.line_ids.filtered(
            lambda r: r.account_id == self.journal_id.default_account_id
        )
        suspense_aml = self.move_id.line_ids - liquidity_aml
        to_reconcile = []
        for i, vals in enumerate(amls_vals):
            balance = vals.get("balance")
            if balance:
                vals["debit"] = balance > 0 and balance or 0.0
                vals["credit"] = balance < 0 and -balance or 0.0
                vals.pop("balance")
            counterpart_aml_id = vals.pop("counterpart_aml_id", False)
            if i == 0:
                aml = suspense_aml
                aml.write(vals)
            else:
                vals["move_id"] = self.move_id.id
                aml = self.env["accoount.move.line"].create(vals)
            if counterpart_aml_id:
                cp_aml = self.env["account.move.line"].browse(counterpart_aml_id)
                to_reconcile.append(aml + cp_aml)
        self.move_id._post()
        [x.reconcile() for x in to_reconcile]
