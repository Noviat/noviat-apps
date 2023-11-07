# Copyright 2009-2023 Noviat.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError

READONLY_IMPORT_FORMATS = ["camt053", "cfonb120", "coda"]


class AccountBankStatement(models.Model):
    _inherit = ["account.bank.statement", "mail.thread"]
    _name = "account.bank.statement"

    name = fields.Char(
        states={"draft": [("readonly", False)]},
        readonly=True,
    )
    accounting_date = fields.Date(
        help="If set, the accounting entries associated with the "
        "bank statement transactions will default to this date.\n"
        "This is useful if the accounting period in which the entries "
        "should normally be booked is already closed.",
        states={"open": [("readonly", False)]},
        readonly=True,
    )
    all_lines_processed = fields.Boolean(
        compute="_compute_all_lines_processed",
        help="Technical field indicating that all statement lines are processed.",
    )
    foreign_currency = fields.Boolean(compute="_compute_foreign_currency", store=True)
    import_format = fields.Char(
        readonly=True,
        help="Manual encoding is assumed when import_format is not set.\n"
        "With manual encoding fields such as journal_id, balance_start, "
        "balance_end_real are always editable for 'draft' statements.",
    )
    import_format_readonly = fields.Boolean(
        compute="_compute_import_format_readonly",
        store=True,
        help="Technical field that is set by the import_format.\n"
        "The following statement fields become readonly when this flag is set:\n"
        "date, balance_start, balance_end_real, journal_id.",
    )
    journal_id = fields.Many2one(
        readonly=False,
    )
    move_line_ids = fields.One2many(
        comodel_name="account.move.line",
        inverse_name="statement_id",
        string="Journal Items",
        readonly=True,
    )
    move_line_count = fields.Integer(compute="_compute_move_line_count")
    state = fields.Selection(
        string="Status",
        required=True,
        readonly=True,
        copy=False,
        tracking=True,
        selection=[
            ("draft", "Draft"),
            ("confirm", "Confirm"),
        ],
        default="draft",
    )

    @api.constrains("name", "journal_id", "date")
    def _check_name(self):
        for rec in self:
            if not all([rec.name, rec.journal_id, rec.date]):
                continue
            dup = self.search_count(
                [
                    ("id", "!=", rec.id),
                    ("name", "=", rec.name),
                    ("journal_id", "=", rec.journal_id.id),
                    ("date", "=", rec.date),
                ]
            )
            if dup:
                message = _(
                    "Statement %(st_name)s, Journal %(journal)s, dated %(date)s "
                    "has already been encoded.",
                    st_name=rec.name,
                    journal=rec.journal_id.name,
                    date=rec.date,
                )
                raise UserError(message)

    @api.depends("import_format")
    def _compute_import_format_readonly(self):
        for rec in self:
            rec.import_format_readonly = rec.import_format in READONLY_IMPORT_FORMATS

    @api.depends("line_ids.is_reconciled")
    def _compute_all_lines_processed(self):
        for rec in self:
            rec.all_lines_processed = all(x.is_reconciled for x in rec.line_ids)

    @api.depends("currency_id")
    def _compute_foreign_currency(self):
        for rec in self:
            if rec.currency_id != rec.company_id.currency_id:
                rec.foreign_currency = True
            else:
                rec.foreign_currency = False

    @api.depends("line_ids.internal_index", "line_ids.state")
    def _compute_date_index(self):
        """
        Replace this method to work on transaction_date i.s.o. date.
        """
        for stmt in self:
            sorted_lines = stmt.line_ids.sorted("internal_index")
            stmt.first_line_index = sorted_lines[:1].internal_index
            if not stmt.date:
                stmt.date = sorted_lines.transaction_date

    @api.depends("line_ids.journal_id")
    def _compute_journal_id(self):
        for rec in self:
            if not rec.journal_id:
                super(AccountBankStatement, rec)._compute_journal_id()
        return

    @api.depends("move_line_ids")
    def _compute_move_line_count(self):
        for statement in self:
            statement.move_line_count = len(statement.move_line_ids)

    def unlink(self):
        for rec in self:
            if rec.state == "confirm":
                raise UserError(
                    _("It is not allowed to remove a confirmed Bank Statement.")
                )
            if rec.import_format in READONLY_IMPORT_FORMATS:
                rec.line_ids.unlink()
        return super().unlink()

    def set_to_draft(self):
        return self.write({"state": "draft"})

    def set_to_confirm(self):
        return self.write({"state": "confirm"})

    def view_journal_entries(self):
        return {
            "name": _("Journal Entries"),
            "view_mode": "tree",
            "res_model": "account.move.line",
            "view_id": self.env.ref("account.view_move_line_tree_grouped_bank_cash").id,
            "type": "ir.actions.act_window",
            "domain": [("move_id", "in", self.line_ids.move_id.ids)],
            "context": {
                "journal_id": self.journal_id.id,
                "group_by": "move_id",
                "expand": True,
            },
        }

    def reconcile_bank_statement_transactions(self):
        self.ensure_one()
        act_oe = "action_open_bank_reconcile_widget"
        if hasattr(self, act_oe):
            return getattr(self, act_oe)()
        elif "account.reconcile.abstract" in self.env:  # account_reconcile_oca
            act_name = "account_reconcile_oca.action_bank_statement_line_reconcile"
            action = self.env["ir.actions.actions"]._for_xml_id(act_name)
            action["domain"] = [
                ("statement_id", "=", self.id),
                ("is_reconciled", "=", False),
            ]
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
        for st in self:
            reconcile_note += st._automatic_reconcile(reconcile_note=reconcile_note)
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

    def _automatic_reconcile(self, reconcile_note="", st_lines=None):
        """
        Placeholder for modules that implement automatic reconciliation (e.g.
        l10n_be_coda_advanced) as a preprocessing step before entering
        into the standard addons javascript reconciliation screen.
        This screen has also an 'auto_reconcile' option but unfortunately
        - too much hardcoded
        - risks on wrong reconciles
        - too late in the process (the javascript screen is not usable for
          lorge statements hence pre-processing is required)
        """
        self.ensure_one()
        return reconcile_note
