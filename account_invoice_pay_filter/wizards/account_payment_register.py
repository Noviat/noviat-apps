# Copyright 2009-2021 Noviat
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        res["journal_id"] = False
        return res

    @api.onchange("journal_id", "invoice_ids")
    def _onchange_journal(self):
        res = super()._onchange_journal()
        if not self.invoice_ids:
            return res
        if not res:
            pj_dom = [
                ("company_id", "=", self.env.company.id),
                ("type", "in", ("bank", "cash")),
            ]
            res["domain"] = {}
        else:
            pj_dom = res["domain"]["journal_id"]
        inv0 = self.invoice_ids[0]
        if inv0.is_inbound():
            pj_dom.append(("payment_method_in", "=", True))
        else:
            pj_dom.append(("payment_method_out", "=", True))
        pay_journals = self.env["account.journal"].search(pj_dom)
        pj_dom = [("id", "in", pay_journals.ids)]
        res["domain"]["journal_id"] = pj_dom
        return res
