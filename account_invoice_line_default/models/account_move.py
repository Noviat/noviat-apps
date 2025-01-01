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
        product_lines = self.filtered(
            lambda line: line.display_type == "product" and line.move_id.is_invoice()
        )
        for product_line in product_lines:
            if (
                product_line.partner_id
                and product_line.partner_id.commercial_partner_id.property_in_inv_account_id
                and product_line.move_type in ["in_invoice", "in_refund"]
            ):
                product_line.account_id = (
                    product_line.partner_id.commercial_partner_id.property_in_inv_account_id
                )
            elif (
                product_line.partner_id
                and product_line.partner_id.commercial_partner_id.property_out_inv_account_id
                and product_line.move_type in ["out_invoice", "out_refund"]
            ):
                product_line.account_id = (
                    product_line.partner_id.commercial_partner_id.property_out_inv_account_id
                )
            else:
                super(AccountMoveLine, product_line)._compute_account_id()
        lines = self - product_lines
        return super(AccountMoveLine, lines)._compute_account_id()
