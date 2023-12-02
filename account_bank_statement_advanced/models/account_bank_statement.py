# Copyright 2009-2021 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountBankStatement(models.Model):
    _inherit = "account.bank.statement"

    accounting_date = fields.Date(
        string="Accounting Date",
        help="If set, the accounting entries associated with the "
        "bank statement transactions will default to this date.\n"
        "This is useful if the accounting period in which the entries "
        "should normally be booked is already closed.",
        states={"open": [("readonly", False)]},
        readonly=True,
    )
    foreign_currency = fields.Boolean(compute="_compute_foreign_currency", store=True)

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

    @api.depends("currency_id")
    def _compute_foreign_currency(self):
        for rec in self:
            if rec.currency_id != rec.company_id.currency_id:
                rec.foreign_currency = True
            else:
                rec.foreign_currency = False

    def automatic_reconcile(self):
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
