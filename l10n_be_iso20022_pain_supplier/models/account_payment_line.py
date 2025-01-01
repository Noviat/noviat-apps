# Copyright 2009-2024 Noviat.
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
            ]._check_bbacomm(apl.communication):
                raise UserError(_("Invalid OGM-VCS Structured Communication !"))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            comm = vals.get("communication")
            comm_type = vals.get("communication_type")
            if comm_type == "BBA":
                vals["communication"] = self.env["account.move"]._format_bbacomm(comm)
        return super().create(vals_list)

    def write(self, vals):
        for rec in self:
            comm = vals.get("communication")
            comm_type = vals.get("communication_type")
            if comm or comm_type:
                comm_type = comm_type or rec.communication_type
                if comm_type == "BBA":
                    comm = comm or rec.communication
                    vals["communication"] = self.env["account.move"]._format_bbacomm(
                        comm
                    )
        return super().write(vals)

    def _prepare_account_payment_vals(self):
        vals = super()._prepare_account_payment_vals()
        if self.mapped("communication_type") == ["BBA"]:
            vals["payment_reference"] = (
                vals["payment_reference"].replace("+", "").replace("/", "")
            )
        return vals
