# Copyright 2009-2021 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.addons.account_bank_statement_advanced.hooks import pre_init_hook


def migrate(cr, version):
    if not version:
        return

    pre_init_hook(cr)
