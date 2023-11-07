# Copyright 2009-2023 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

from odoo import SUPERUSER_ID, api
from odoo.models import MAGIC_COLUMNS


def _pre_init_hook(cr):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _update_be_banks(env)


def _post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _update_be_partner_banks(env)


def _update_be_banks(env):

    # in 8.0 this module was called l10n_be_partner
    # we clean also trailing 8.0 ir.model_data entries
    env.cr.execute(
        """
    DELETE FROM ir_model_data
    WHERE module in ('l10n_be_partner', 'l10n_be_partner_bank')
    AND model='res.bank'
       """
    )

    env.cr.execute(
        """
    SELECT * FROM res_bank
    WHERE SUBSTRING(REPLACE(bic, ' ', '') FROM 5 FOR 2) = 'BE'
    ORDER BY id
        """
    )
    be_bank_datas = env.cr.dictfetchall()

    # delete unused banks
    env.cr.execute("SELECT bank_id FROM res_partner_bank WHERE bank_id IS NOT NULL")
    used_ids = {x[0] for x in env.cr.fetchall()}
    unused_ids = [x["id"] for x in be_bank_datas if x["id"] not in used_ids]
    if unused_ids:
        env.cr.execute(
            "DELETE FROM res_bank WHERE id in %s",
            (tuple(unused_ids),),
        )
    be_bank_datas = [x for x in be_bank_datas if x["id"] in used_ids]
    for be_bank_data in be_bank_datas:
        be_bank_data["bic"] = be_bank_data["bic"].replace("XXX", "")

    # create XML_IDS for used banks and merge duplicates
    merged = []
    env.cr.execute("SELECT res_id FROM ir_model_data WHERE module='base' and name='be'")
    be_country_id = env.cr.fetchone()[0]
    exclude = (
        MAGIC_COLUMNS + [env["res.bank"].CONCURRENCY_CHECK_FIELD] + ["country", "bic"]
    )
    bank_fields = env["res.bank"]._fields
    bank_field_names = [
        x for x in bank_fields if x not in exclude and bank_fields[x].store
    ]
    for be_bank_data in be_bank_datas:
        dups = [
            x
            for x in be_bank_datas
            if x["id"] != be_bank_data["id"] and x["bic"] == be_bank_data["bic"]
        ]
        dup_ids = [x["id"] for x in dups]
        if dup_ids:
            env.cr.execute(
                """
            UPDATE res_partner_bank
            SET bank_id = %s
            WHERE bank_id in %s
                """,
                (be_bank_data["id"], tuple(dup_ids)),
            )
        merged.extend(dup_ids)
        vals = {}
        bic = be_bank_data["bic"]
        if " " in be_bank_data["bic"]:
            bic = bic.replace(" ", "")
            vals["bic"] = bic
        for dup in dups:
            for fld in bank_field_names:
                if dup[fld] and not be_bank_data[fld]:
                    vals[fld] = dup[fld]
        if not be_bank_data.get("country") or be_bank_data["country"] != be_country_id:
            vals["country"] = be_country_id
        if vals:
            sql = "UPDATE res_bank SET "
            updates = []
            for fld in vals:
                if bank_fields[fld].type == "char":
                    upd_str = "{fld} = '{val}'"
                elif bank_fields[fld].type == "many2one":
                    upd_str = "{fld} = {val}"
                else:
                    continue  # only char and m2o are supported
                updates.append(upd_str.format(fld=fld, val=vals[fld]))
            sql += ", ".join(updates)
            sql += " WHERE id = {id}".format(id=be_bank_data["id"])
            env.cr.execute(sql)
        openupgrade.add_xmlid(
            env.cr,
            "l10n_be_partner_bank",
            "res_bank_{}".format(bic),
            "res.bank",
            be_bank_data["id"],
            noupdate=True,
        )
    if merged:
        env.cr.execute("DELETE from res_bank WHERE id in %s", (tuple(merged),))


def _update_be_partner_banks(env):
    """
    write on acc_number to set bank_id
    """
    be_partner_banks = env["res.partner.bank"].search([("acc_number", "=ilike", "BE")])
    [x.write({"acc_number": x.acc_number}) for x in be_partner_banks]
