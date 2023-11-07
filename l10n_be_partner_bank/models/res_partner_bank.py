# Copyright 2009-2023 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, models
from odoo.exceptions import UserError

from odoo.addons.base_iban.models.res_partner_bank import normalize_iban

from .res_bank import COUNTRY_CODES


class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    @api.model_create_multi
    def create(self, vals_list):
        [self._update_partner_bank_vals(vals) for vals in vals_list]
        return super().create(vals_list)

    def write(self, vals):
        if "bank_id" in vals or "acc_number" in vals:
            for rec in self:
                if "bank_id" not in vals:
                    vals["bank_id"] = rec.bank_id.id
                if "acc_number" not in vals:
                    vals["acc_number"] = rec.acc_number
                self._update_partner_bank_vals(vals)
        return super().write(vals)

    def _update_partner_bank_vals(self, vals):
        self._bban2iban(vals)
        if (
            vals.get("acc_number")
            and self.retrieve_acc_type(vals["acc_number"]) == "iban"
        ):
            country_code = vals["acc_number"][:2].upper()
            if country_code in COUNTRY_CODES:
                # TODO: make PR to standard Odoo addons/base_iban
                # the pretty_iban function should to the upper()
                vals["acc_number"] = vals["acc_number"].upper()
                self._update_partner_bank_vals_with_bank(country_code, vals)

    def _bban2iban(self, vals):
        if (
            vals.get("bank_id")
            and vals.get("acc_number")
            and vals["acc_number"].strip()[0].isdigit()
        ):
            bank = self.env["res.bank"].search(
                [("id", "=", vals["bank_id"]), ("country.code", "in", COUNTRY_CODES)]
            )
            if bank:
                vals["acc_number"] = self.env["res.bank"]._bban2iban(
                    bank.country.code, vals["acc_number"]
                )

    def _update_partner_bank_vals_with_bank(self, country_code, vals):
        iban = normalize_iban(vals["acc_number"])
        if country_code == "BE":
            bban_code = iban[4:7]
            bank_ids = (
                self.env["res.bank"]
                ._search([("bban_code_list", "ilike", bban_code)])
                ._result
            )
            if bank_ids:
                if len(bank_ids) > 1:
                    raise UserError(
                        _(
                            "Duplicate bank records found for BBAN Code '%{bban_code}%'.",
                            bban_code=bban_code,
                        )
                    )
                vals["bank_id"] = bank_ids[0]
