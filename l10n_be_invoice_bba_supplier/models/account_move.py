# Copyright 2009-2020 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    supplier_payment_ref_type = fields.Selection(
        selection="_selection_supplier_payment_ref_type",
        string="Payment Reference Type",
        default="normal",
        copy=False,
    )

    @api.model
    def _selection_supplier_payment_ref_type(self):
        return [
            ("normal", _("Free Communication")),
            ("bba", _("Belgian OGM-VCS Structured Communication")),
        ]

    @api.constrains("invoice_payment_ref", "supplier_payment_ref_type")
    def _check_invoice_payment_ref(self):
        for inv in self:
            if inv.supplier_payment_ref_type == "bba" and not self.check_bbacomm(
                inv.invoice_payment_ref
            ):
                raise UserError(_("Invalid OGM-VCS Structured Communication !"))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            inv_type = vals.get("type") or self.env.context.get("default_type")
            if (
                inv_type != "in_invoice"
                or vals.get("supplier_payment_ref_type") != "bba"
            ):
                continue

            pay_ref = vals.get("invoice_payment_ref")
            if self.check_bbacomm(pay_ref):
                vals["invoice_payment_ref"] = self._format_bbacomm(pay_ref)

        return super().create(vals_list)

    def write(self, vals):
        for inv in self:
            if inv.state == "draft":
                if "supplier_payment_ref_type" in vals:
                    pay_ref_type = vals["supplier_payment_ref_type"]
                else:
                    pay_ref_type = inv.supplier_payment_ref_type
                if pay_ref_type == "bba":
                    if "invoice_payment_ref" in vals:
                        bbacomm = vals["invoice_payment_ref"]
                    else:
                        bbacomm = inv.invoice_payment_ref or ""
                    if self.check_bbacomm(bbacomm):
                        vals["invoice_payment_ref"] = self._format_bbacomm(bbacomm)
        return super().write(vals)

    def check_bbacomm(self, val):
        supported_chars = "0-9+*/ "
        pattern = re.compile("[^" + supported_chars + "]")
        if pattern.findall(val or ""):
            return False
        bbacomm = re.sub(r"\D", "", val or "")
        if len(bbacomm) == 12:
            base = int(bbacomm[:10])
            mod = base % 97 or 97
            if mod == int(bbacomm[-2:]):
                return True
        return False

    def _format_bbacomm(self, val):
        bba = re.sub(r"\D", "", val)
        bba = "+++{}/{}/{}+++".format(bba[0:3], bba[3:7], bba[7:])
        return bba
