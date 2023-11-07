# Copyright 2009-2020 Noviat.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from openupgradelib import openupgrade  # pylint: disable=W7936


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.load_data(
        env.cr,
        "account_bank_statement_advanced",
        "migrations/13.0.1/noupdate_changes.xml",
    )
