# Copyright 2009-2023 Noviat.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from openupgradelib import openupgrade


def migrate(cr, version):
    if not version:
        return

    openupgrade.rename_xmlids(
        cr,
        [
            (
                "account_bank_statement_advanced.sequence_reconcile_seq",
                "account_bank_statement_advanced.ir_sequence_st_line_glob",
            ),
        ],
    )
