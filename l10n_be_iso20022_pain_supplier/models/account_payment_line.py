# Copyright 2009-2021 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountPaymentLine(models.Model):
    _inherit = "account.payment.line"

    communication_type = fields.Selection(
        selection_add=[("BBA", _("Belgian OGM-VCS Structured Communication"))],
        ondelete={"BBA": "set default"},
    )

    @api.constrains("communication", "communication_type")
    def _check_invoice_payment_ref(self):
        for apl in self:
            if apl.communication_type == "BBA" and not self.env[
                "account.move"
            ].check_bbacomm(apl.communication):
                raise UserError(_("Invalid OGM-VCS Structured Communication !"))
