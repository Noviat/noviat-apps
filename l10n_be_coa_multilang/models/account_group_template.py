# Copyright 2009-2021 Noviat
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountGroupTemplate(models.Model):
    _name = "account.group.template"
    _description = "Template for Account Groups"
    _order = "code_prefix"

    code_prefix = fields.Char()
    name = fields.Char(required=True, translate=True)
    parent_id = fields.Many2one(
        comodel_name="account.group.template", ondelete="cascade"
    )
    chart_template_id = fields.Many2one(
        comodel_name="account.chart.template", string="Chart Template", required=True
    )
