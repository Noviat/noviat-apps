# Copyright 2009-2021 Noviat
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountGroup(models.Model):
    _inherit = "account.group"

    name = fields.Char(translate=True)
    company_id = fields.Many2one(
        comodel_name="res.company", default=lambda self: self._default_company_id()
    )

    @api.model
    def _default_company_id(self):
        return self.env.company

    def search(self, args, offset=0, limit=None, order=None, count=False):
        company_id = self.env.context.get("force_company")
        if company_id:
            args.extend([("company_id", "=", company_id)])
        return super().search(
            args, offset=offset, limit=limit, order=order, count=count
        )
