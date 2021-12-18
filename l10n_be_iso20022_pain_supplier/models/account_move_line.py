# Copyright 2009-2021 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _prepare_payment_line_vals(self, payment_order):
        vals = super()._prepare_payment_line_vals(payment_order)
        communication_type = self.move_id.supplier_payment_ref_type
        if "communication" in vals and communication_type == "bba":
            comm = self.move_id.payment_reference
            vals.update(
                {
                    "communication": comm.replace("+", "").replace("/", ""),
                    "communication_type": "BBA",
                }
            )
        return vals
