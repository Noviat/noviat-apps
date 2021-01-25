# Copyright 2009-2020 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, fields, models
from odoo.exceptions import UserError


class AccountTax(models.Model):
    _inherit = "account.tax"

    def unlink(self):
        self._unlink_check_products()
        self._unlink_check_account_move_lines()
        return super().unlink()

    def _unlink_check_products(self):
        for tax in self:
            products = (
                self.env["product.template"]
                .with_context(active_test=False)
                .search(
                    ["|", ("supplier_taxes_id", "=", tax.id), ("taxes_id", "=", tax.id)]
                )
            )
            if products:
                product_list = ["%s" % x.name for x in products]
                raise UserError(
                    _(
                        "You cannot delete a tax that "
                        "has been set on product records"
                        "\nAs an alterative, you can disable a "
                        "tax via the 'active' flag."
                        "\n\nProduct records: %s"
                    )
                    % product_list
                )

    def _unlink_check_account_move_lines(self):
        for tax in self:
            aml_ids = []
            self.env.cr.execute(  # pylint: disable=E8103
                """
                SELECT id
                FROM account_move_line
                WHERE tax_line_id = %s
                """
                % tax.id
            )
            res = self.env.cr.fetchall()
            if res:
                aml_ids += [x[0] for x in res]

            self.env.cr.execute(  # pylint: disable=E8103
                """
                SELECT account_move_line_id
                FROM account_move_line_account_tax_rel
                WHERE account_tax_id = %s
                """
                % tax.id
            )
            res = self.env.cr.fetchall()
            if res:
                aml_ids += [x[0] for x in res if x[0] not in aml_ids]

            for atrl in (
                tax.invoice_repartition_line_ids + tax.refund_repartition_line_ids
            ):
                self.env.cr.execute(  # pylint: disable=E8103
                    """
                    SELECT id
                    FROM account_move_line
                    WHERE tax_repartition_line_id = %s
                    """
                    % atrl.id
                )
                res = self.env.cr.fetchall()
                if res:
                    aml_ids += [x[0] for x in res if x[0] not in aml_ids]

            if aml_ids:
                raise UserError(
                    _(
                        "You cannot delete a tax that "
                        "has been set on Journal Items."
                        "\n\nJournal Item IDs: %s"
                    )
                    % aml_ids
                )


class AccountTaxRepartitionLine(models.Model):
    _inherit = "account.tax.repartition.line"

    # bugfix: delete repartition lines when tax is deleted
    invoice_tax_id = fields.Many2one(ondelete="cascade")
    refund_tax_id = fields.Many2one(ondelete="cascade")
