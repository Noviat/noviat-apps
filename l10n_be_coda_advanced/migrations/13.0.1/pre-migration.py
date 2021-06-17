# Copyright 2009-2020 Noviat
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

_field_renames = [
    (
        "coda.bank.account",
        "coda_bank_account",
        "transfer_account",
        "transfer_account_id",
    )
]


@openupgrade.migrate()
def migrate(env, version):
    table = _field_renames[0][1]
    column_old = _field_renames[0][2]
    column_new = _field_renames[0][3]
    if openupgrade.column_exists(env.cr, table, column_old):
        if not openupgrade.column_exists(env.cr, table, column_new):
            openupgrade.rename_fields(env, _field_renames)
        else:
            env.cr.execute(
                "UPDATE coda_bank_account SET transfer_account_id=transfer_account"
            )
