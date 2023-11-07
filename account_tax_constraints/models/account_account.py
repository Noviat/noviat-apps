# Copyright 2009-2023 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, models
from odoo.exceptions import UserError


class AccountAccount(models.Model):
    _inherit = "account.account"

    @api.ondelete(at_uninstall=False)
    def _unlink_except_linked_to_tax(self):
        for rec in self:
            tax_ids = (
                self.env["account.tax"]
                .with_context(active_test=False)
                ._search([("cash_basis_transition_account_id", "=", rec.id)])
                ._result
            )
            if tax_ids:
                raise UserError(
                    _(
                        "You cannot delete an account that "
                        "has been set on tax objects."
                        "\nAccount: %(account)s"
                        "\nTax Object IDs: %(tax_ids)s"
                    )
                    % {"account": rec.code, "tax_ids": tax_ids}
                )
