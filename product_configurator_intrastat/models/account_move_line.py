# Copyright 2021 Noviat (<https://www.noviat.com>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    config_session_id = fields.Many2one(
        comodel_name="product.config.session", string="Config Session"
    )
