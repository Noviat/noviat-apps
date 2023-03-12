# Copyright 2009-2023 Noviat
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class ResCompany(models.Model):
    _inherit = "res.company"

    @api.depends("vat", "country_id")
    def _compute_company_registry(self):
        super()._compute_company_registry()
        for company in self.filtered(
            lambda comp: comp.country_id.code == "BE" and comp.vat
        ):
            vat_country, vat_number = self.env["res.partner"]._split_vat(company.vat)
            if vat_country == "be" and self.env["res.partner"].simple_vat_check(
                vat_country, vat_number
            ):
                company.company_registry = vat_number
        return
