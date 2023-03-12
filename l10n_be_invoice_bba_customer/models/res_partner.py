# Copyright 2009-2023 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    out_inv_comm_algorithm = fields.Selection(
        selection="_selection_out_inv_comm_algorithm",
        company_dependent=True,
        string="Communication Algorithm",
        help="Select Algorithm to generate the "
        "Structured Communication on Outgoing Invoices.",
    )
    out_inv_comm_type = fields.Selection(
        selection="_selection_out_inv_comm_type",
        string="Communication Type",
        change_default=True,
        default="normal",
        company_dependent=True,
        help="Select Default Communication Type for Outgoing Invoices.",
    )

    @api.model
    def _selection_out_inv_comm_type(self):
        return [
            ("normal", _("Free Communication")),
            ("bba", _("Belgian OGM-VCS Structured Communication")),
        ]

    @api.model
    def _selection_out_inv_comm_algorithm(self):
        return [
            ("random", "Random"),
            ("date", "Date"),
            ("partner_ref", "Customer Reference"),
        ]
