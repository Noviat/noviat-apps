# Copyright 2009-2022 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class ResCurrency(models.Model):
    _inherit = "res.currency"

    def _get_rates(self, company, date):
        date = self.env.context.get("rate_date") or date
        return super()._get_rates(company, date)
