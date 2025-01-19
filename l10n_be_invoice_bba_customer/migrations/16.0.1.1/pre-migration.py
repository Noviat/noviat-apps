# Copyright 2009-2024 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.rename_fields(
        env,
        [("res.partner", "res.partner", "out_inv_comm_type", "out_inv_comm_standard")],
    )
