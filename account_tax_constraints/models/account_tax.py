# Copyright 2009-2024 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, models
from odoo.exceptions import UserError


class AccountTax(models.Model):
    _inherit = "account.tax"

    @api.ondelete(at_uninstall=False)
    def _unlink_except_linked_to_product(self):
        for tax in self:
            products = (
                self.env["product.template"]
                .with_context(active_test=False)
                .search(
                    ["|", ("supplier_taxes_id", "=", tax.id), ("taxes_id", "=", tax.id)]
                )
            )
            if products:
                product_list = ", ".join([f"{x.name} (ID:{x.id})" for x in products])
                raise UserError(
                    _(
                        "You cannot delete a tax that "
                        "has been set on product records"
                        "\nAs an alterative, you can disable a "
                        "tax via the 'active' flag."
                        "\n\nProduct Template records: %s"
                    )
                    % product_list
                )

    @api.ondelete(at_uninstall=False)
    def _unlink_except_linked_to_account_move_line(self):
        """
        This method could be dropped since Odoo protects this operation
        via FK constraint but the FK constraint error message doesn't
        give information on the impacted records, hence we prefer to maintain
        this method.
        """
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
