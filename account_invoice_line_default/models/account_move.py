# Copyright 2009-2024 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    invoice_description = fields.Char(
        string="Description",
        index=True,
        readonly=True,
        copy=False,
        help="This field will also be used as a default label on the invoice lines",
    )


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _compute_account_id(self):
        lines = self.filtered(
            lambda line: line.display_type == "product" and line.move_id.is_invoice()
        )
        commercial_partner = lines and lines[0].partner_id.commercial_partner_id
        for line in lines:
            if (
                line.partner_id
                and commercial_partner.property_in_inv_account_id
                and line.move_type in ["in_invoice", "in_refund"]
            ):
                line.account_id = commercial_partner.property_in_inv_account_id
            elif (
                line.partner_id
                and commercial_partner.property_out_inv_account_id
                and line.move_type in ["out_invoice", "out_refund"]
            ):
                line.account_id = commercial_partner.property_out_inv_account_id
            else:
                super(AccountMoveLine, line)._compute_account_id()
        lines = self - lines
        return super(AccountMoveLine, lines)._compute_account_id()
