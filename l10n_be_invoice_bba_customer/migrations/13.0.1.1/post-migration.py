# Copyright 2009-2023 Noviat
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    cr.execute(
        """
        SELECT id, company_id, out_inv_comm_algorithm, out_inv_comm_type
        FROM res_partner
        WHERE out_inv_comm_algorithm IS NOT NULL
           OR COALESCE(out_inv_comm_type) = 'bba';
        """
    )
    res = cr.dictfetchall()
    for entry in res:
        p_mod = env["res.partner"].with_context(force_company=entry["company_id"])
        partner = p_mod.browse(entry["id"])
        partner.out_inv_comm_algorithm = entry["out_inv_comm_algorithm"]
        partner.out_inv_comm_type = entry["out_inv_comm_type"]
