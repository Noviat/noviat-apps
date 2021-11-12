# Copyright 2021 Noviat (<https://www.noviat.com>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


from odoo import models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _prepare_invoice_line(self):
        res = super()._prepare_invoice_line()
        res.update({"config_session_id": self.config_session_id})
        return res
