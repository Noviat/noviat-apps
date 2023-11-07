# Copyright 2009-2023 Noviat
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

# pylint: disable=W8150
from odoo.addons.l10n_be_partner_bank.hooks import _update_be_banks


@openupgrade.migrate()
def migrate(env, version):
    _update_be_banks(env)
