# Copyright 2009-2021 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    _inherit = "account.payment"

    @api.onchange("amount", "currency_id")
    def _onchange_amount(self):
        ctx = dict(self.env.context, account_invoice_pay_filter_onchange_amount=True)
        # we need to call super with special context since the super assigns otherwise
        # the first financial journal returned by search on account.journal.
        res = super(AccountPayment, self.with_context(ctx))._onchange_amount()
        if not res and not res.get("domain") and not res["domain"].get("journal_id"):
            _logger.error(
                "Programming Error in _on_change amount. "
                "The method does not return the journal domain."
            )
            return res
        pj_dom = res["domain"]["journal_id"]
        if self.payment_type == "inbound":
            pj_dom.append(("payment_method_in", "=", True))
        else:
            pj_dom.append(("payment_method_out", "=", True))
        pay_journals = self.env["account.journal"].search(pj_dom)
        if len(pay_journals) == 1:
            self.journal_id = pay_journals
        pj_dom = [("id", "in", pay_journals.ids)]
        res["domain"]["journal_id"] = pj_dom
        _logger.error("_onchange_amount, exit, res=%s", res)
        return res

    @api.onchange("journal_id")
    def _onchange_journal(self):
        res = super()._onchange_journal()
        # The standard Odoo code does not reset currency in case
        # of company currency. We fix this bug here.
        # TODO: make PR for odoo.
        if self.journal_id:
            currency = (
                self.journal_id.currency_id or self.journal_id.company_id.currency_id
            )
            if self.currency_id != currency:
                self.currency_id = currency
        if self.journal_id and len(self.invoice_ids) == 1:
            if (
                self.payment_type == "inbound"
                and self.journal_id.payment_date_in == "invoice_date"
            ):
                self.payment_date = self.invoice_ids.invoice_date
            elif self.journal_id.payment_date_out == "invoice_date":
                self.payment_date = self.invoice_ids.invoice_date
        return res
