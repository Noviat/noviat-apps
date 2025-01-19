# Copyright 2009-2024 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    out_inv_comm_standard = fields.Selection(
        selection="_selection_out_inv_comm_standard",
        string="Communication Standard",
        change_default=True,
        company_dependent=True,
        help="Select Communication Standard for Outgoing Invoices.\n"
        "This setting will only be effective when you create your Customer "
        "Invoices via a Sales Journal with Communication Standard "
        "set to 'Defined on Customer record'.",
    )
    out_inv_comm_algorithm = fields.Selection(
        selection="_selection_out_inv_comm_algorithm",
        company_dependent=True,
        string="Communication Algorithm",
        help="Select Algorithm to generate the "
        "Structured Communication on Outgoing Invoices.",
    )
    invoice_reference_type_odoo = fields.Selection(
        selection="_selection_invoice_reference_type_odoo",
        company_dependent=True,
        help="Select Algorithm to generate the "
        "Structured Communication on Outgoing Invoices.",
    )
    invoice_reference_type = fields.Selection(
        selection="_selection_invoice_reference_type",
        company_dependent=True,
        help="Select Algorithm to generate the "
        "Structured Communication on Outgoing Invoices.",
    )

    @api.model
    def _selection_out_inv_comm_standard(self):
        selection = (
            self.env["account.journal"]._fields["invoice_reference_model"].selection
        )
        return [x for x in selection if x[0] != "partner"]

    @api.model
    def _selection_out_inv_comm_algorithm(self):
        return [
            ("random", _("Random")),
            ("date", _("Date")),
            ("partner_ref", _("Customer Reference")),
        ]

    @api.model
    def _selection_invoice_reference_type_odoo(self):
        selection = (
            self.env["account.journal"]._fields["invoice_reference_type"].selection
        )
        return selection

    @api.model
    def _selection_invoice_reference_type(self):
        selection = self._selection_invoice_reference_type_odoo()
        return [x for x in selection if x[0] != "none"]
