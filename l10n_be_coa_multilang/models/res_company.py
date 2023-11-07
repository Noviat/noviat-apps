# Copyright 2009-2023 Noviat
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class ResCompany(models.Model):
    _inherit = "res.company"

    @api.model_create_multi
    def create(self, vals_list):
        cps = super().create(vals_list)
        for cp in cps:
            cp.partner_id._onchange_vat()
        return cps

    def write(self, vals):
        res = super().write(vals)
        for cp in self:
            cp.partner_id._onchange_vat()
        return res
