# Copyright 2009-2024 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    partners = env["res.partner"].with_context(active_test=False).search([])
    bba_partners = (
        env["res.partner"]
        .with_context(active_test=False)
        .search([("out_inv_comm_standard", "=", "bba")])
    )
    bba_partners.write({"out_inv_comm_standard": "be"})
    other_partners = partners - bba_partners
    other_partners.write(
        {
            "out_inv_comm_standard": "odoo",
            "invoice_reference_type": "invoice",
        }
    )
