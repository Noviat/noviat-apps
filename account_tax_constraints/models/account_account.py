# Copyright 2009-2023 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, models
from odoo.exceptions import UserError


class AccountAccount(models.Model):
    _inherit = "account.account"

    def unlink(self):
        self._unlink_check_taxes()
        return super().unlink()

    def _unlink_check_taxes(self):
        for account in self:

            self.env.cr.execute(  # pylint: disable=E8103
                """
                SELECT id
                FROM account_tax
                WHERE cash_basis_transition_account_id = %(a_id)s
                """
                % {"a_id": account.id}
            )
            res = self.env.cr.fetchall()
            if res:
                tax_ids = [x[0] for x in res]
                raise UserError(
                    _(
                        "You cannot delete an account that "
                        "has been set on tax objects."
                        "\nAccount ID: %(acc_id)s"
                        "\nTax Object IDs: %(tax_ids)s"
                    )
                    % {"acc_id": account.id, "tax_ids": tax_ids}
                )

            self.env.cr.execute(  # pylint: disable=E8103
                """
                SELECT id
                FROM account_tax_repartition_line
                WHERE account_id = %s
                """
                % account.id
            )
            res = self.env.cr.fetchall()
            if res:
                atrl_ids = [x[0] for x in res]
                taxes = (
                    self.env["account.tax.repartition.line"]
                    .browse(atrl_ids)
                    .mapped("tax_id")
                )
                raise UserError(
                    _(
                        "You cannot delete an account that "
                        "has been set on tax objects."
                        "\nAccount ID: %(acc_id)s"
                        "\nTax Object IDs: %(tax_ids)s"
                    )
                    % {"acc_id": account.id, "tax_ids": taxes.ids}
                )
