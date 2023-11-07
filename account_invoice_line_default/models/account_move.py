# Copyright 2009-2022 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    invoice_description = fields.Char(
        string="Description",
        index=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
        copy=False,
        help="This field will also be used as a default label on the invoice lines",
    )


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _compute_account_id(self):
        for move in self:
            if (
                move.partner_id
                and move.partner_id.commercial_partner_id.property_in_inv_account_id
                and move.move_type in ["in_invoice", "in_refund"]
            ):
                move.account_id = (
                    move.partner_id.commercial_partner_id.property_in_inv_account_id
                )
            elif (
                move.partner_id
                and move.partner_id.commercial_partner_id.property_out_inv_account_id
                and move.move_type in ["out_invoice", "out_refund"]
            ):
                move.account_id = (
                    move.partner_id.commercial_partner_id.property_out_inv_account_id
                )
            else:
                super(AccountMoveLine, move)._compute_account_id()
        return
