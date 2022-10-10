# Copyright 2009-2022 Noviat (http://www.noviat.com).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, models


class IrConfigParameter(models.Model):
    _inherit = "ir.config_parameter"

    @api.model
    def get_web_tree_date_search_parameters(self):
        opts = [
            "web_tree_date_search.applicability",
        ]
        return {
            res["key"]: res["value"]
            for res in self.sudo().search_read([["key", "in", opts]], ["key", "value"])
        }
