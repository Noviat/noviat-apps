# Copyright 2009-2024 Noviat
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models

from odoo.addons.account.models.account_account import AccountAccount as AML_AA


class AccountAccount(models.Model):
    _inherit = "account.account"

    name = fields.Char(translate=False)

    def copy_translations(self, new, excluded=()):
        if self._fields["name"].translate:
            return super().copy_translations(new, excluded=excluded)
        else:
            return super(AML_AA, self).copy_translations(new, excluded=excluded)
