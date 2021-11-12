# Copyright 2009-2021 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResCountry(models.Model):
    _inherit = "res.country"

    clearing_system_identification = fields.Char(
        help="ClearingSystemIdentification <ClrSysId> field, ISO20022 payments"
    )
