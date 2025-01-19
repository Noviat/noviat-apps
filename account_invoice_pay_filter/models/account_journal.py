# Copyright 2009-2024 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    payment_method_out = fields.Boolean(
        string="Outgoing Payment Method",
        help="If checked, this Journal becomes a Payment Method "
        "for the 'Register Payment' button on "
        "Supplier Invoices and Customer Credit Notes.",
    )
    payment_method_in = fields.Boolean(
        string="Incoming Payment Method",
        help="If checked, this Journal becomes a Payment Method "
        "for the 'Register Payment' button on "
        "Customer Invoices and Supplier Credit Notes.",
    )
