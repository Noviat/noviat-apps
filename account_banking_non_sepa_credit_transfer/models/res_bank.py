# Copyright 2009-2021 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResBank(models.Model):
    _inherit = "res.bank"

    clearing_system_member_identification = fields.Char(
        help="MemberIdentification <MmbId> field, ISO20022 payments"
    )
