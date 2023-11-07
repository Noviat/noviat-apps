# Copyright 2009-2021 Noviat.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo.addons.account_bank_statement_advanced.hooks import (  # pylint: disable=W7950,W8150
    pre_init_hook,
)


def migrate(cr, version):
    if not version:
        return

    pre_init_hook(cr)
