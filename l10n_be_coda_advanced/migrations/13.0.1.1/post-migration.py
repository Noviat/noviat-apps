# Copyright 2009-2021 Noviat.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from openupgradelib import openupgrade  # pylint: disable=W7936


@openupgrade.migrate()
def migrate(env, version):

    _noupdate_changes(env, version)


def _noupdate_changes(env, version):
    openupgrade.load_data(
        env.cr, "l10n_be_coda_advanced", "migrations/13.0.1.1/noupdate_changes.xml"
    )
