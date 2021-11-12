# Copyright 2009-2021 Noviat
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """
    Create account groups and assign those groups to the acccounts.
    """
    with api.Environment.manage():
        env = api.Environment(cr, SUPERUSER_ID, {})
        chart_template = env.ref("l10n_be_coa_multilang.l10n_be_coa_multilang_template")
        companies = env["res.company"].search(
            [("chart_template_id", "=", chart_template.id)]
        )
        coa_wiz_mod = env["l10n.be.coa.multilang.config"]
        langs = env["res.lang"].search([])
        lang_codes = {x.code for x in langs if x.code[:2] in ("en", "nl", "fr")}
        group_tmpls = env["account.group.template"].search(
            [("chart_template_id", "=", chart_template.id)], order="code_prefix",
        )
        monolang_coa = coa_wiz_mod._default_monolang_coa()
        for company in companies:
            ctx = {"lang": company.partner_id.lang}
            chart_template = company.chart_template_id.with_context(ctx)
            groups = chart_template._generate_account_groups(company)
            coa_wiz = coa_wiz_mod.create(
                {"company_id": company.id, "monolang_coa": monolang_coa}
            )
            langs_todo = [x for x in lang_codes if x != company.partner_id.lang]
            if not monolang_coa:
                coa_wiz._field_check("code_prefix", group_tmpls, groups)
                coa_wiz._copy_xlat(langs_todo, "name", group_tmpls, groups)
            acc_ctx = {"noupdate_account_type": True, "noupdate_account_tags": True}
            accounts = (
                env["account.account"]
                .with_context(dict(acc_ctx, force_company=company.id))
                .search([("company_id", "=", company.id)])
            )
            for account in accounts:
                account.onchange_code()
