# Copyright 2009-2020 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountTaxTemplate(models.Model):
    _inherit = "account.tax.template"

    code = fields.Char()

    def _get_tax_vals(self, company, tax_template_to_tax):
        vals = super()._get_tax_vals(company, tax_template_to_tax)
        return dict(vals, code=self.code)
