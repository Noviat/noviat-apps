# Copyright 2009-2023 Noviat.
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

    @api.constrains("payment_reference", "supplier_payment_ref_type")
    def _check_payment_reference(self):
        for inv in self:
            if inv.supplier_payment_ref_type == "bba" and not self._check_bbacomm(
                inv.payment_reference
            ):
                raise UserError(_("Invalid OGM-VCS Structured Communication !"))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            inv_type = vals.get("move_type") or self.env.context.get(
                "default_move_type"
            )
            if (
                inv_type != "in_invoice"
                or vals.get("supplier_payment_ref_type") != "bba"
            ):
                continue

            pay_ref = vals.get("payment_reference")
            if self._check_bbacomm(pay_ref):
                vals["payment_reference"] = self._format_bbacomm(pay_ref)

        return super().create(vals_list)

    def write(self, vals):
        for inv in self:
            if inv.state == "draft":
                if "supplier_payment_ref_type" in vals:
                    pay_ref_type = vals["supplier_payment_ref_type"]
                else:
                    pay_ref_type = inv.supplier_payment_ref_type
                if pay_ref_type == "bba":
                    if "payment_reference" in vals:
                        bbacomm = vals["payment_reference"]
                    else:
                        bbacomm = inv.payment_reference or ""
                    if self._check_bbacomm(bbacomm):
                        vals["payment_reference"] = self._format_bbacomm(bbacomm)
        return super().write(vals)

    def _check_bbacomm(self, payment_reference):
        supported_chars = "0-9+*/ "
        pattern = re.compile("[^" + supported_chars + "]")
        if pattern.findall(payment_reference or ""):
            return False
        bbacomm = re.sub(r"\D", "", payment_reference or "")
        if len(bbacomm) == 12:
            base = int(bbacomm[:10])
            mod = base % 97 or 97
            if mod == int(bbacomm[-2:]):
                return True
        return False

    def _format_bbacomm(self, payment_reference):
        bba = re.sub(r"\D", "", payment_reference)
        bba = "+++{}/{}/{}+++".format(bba[0:3], bba[3:7], bba[7:])
        return bba
