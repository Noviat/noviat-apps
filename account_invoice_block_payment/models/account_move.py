# Copyright 2009-2021 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    block_payment = fields.Boolean(
        help="If checked, this Invoice will be excluded from the "
        "Payment Order 'Create Payment Lines' button results.",
    )
