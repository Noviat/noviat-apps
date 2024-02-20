# Copyright 2009-2023 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AccountTax(models.Model):
    _inherit = "account.tax"

    def name_get(self):
        if self.env.context.get("active_model") == "wizard.update.charts.accounts":
            result = []
            for rec in self:
                if rec.code:
                    name = rec.code
                else:
                    name = rec.name[:20] + "..."
                name += " (ID: {})".format(rec.id)
                result.append((rec.id, name))
            return result
        else:
            return super().name_get()
