# Copyright 2009-2020 Noviat
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"
    _order = "name"

    name = fields.Char(translate=True)
    l10n_be_coa_multilang = fields.Boolean(string="Multilang Belgian CoA")

    def get_countries_posting_at_bank_rec(self):
        rslt = super().get_countries_posting_at_bank_rec()
        rslt.append("BE")
        return rslt

    @api.model
    def _prepare_all_journals(self, acc_template_ref, company, journals_dict=None):
        journal_data = super()._prepare_all_journals(
            acc_template_ref, company, journals_dict
        )
        for journal in journal_data:
            if journal["type"] in (
                "sale",
                "purchase",
            ) and company.country_id == self.env.ref("base.be"):
                journal.update({"refund_sequence": True})
        return journal_data

    def _generate_account_groups(self, company):
        """
        Code backported from Odoo 14.0 OC and adapted to set parent_id
        from templates
        """
        self.ensure_one()
        group_templates = self.env["account.group.template"].search(
            [("chart_template_id", "=", self.id)]
        )
        template_vals = []
        for group_template in group_templates:
            vals = {
                "name": group_template.name,
                "code_prefix": group_template.code_prefix,
                "company_id": company.id,
            }
            template_vals.append((group_template, vals))
        groups = self._create_records_with_xmlid(
            "account.group", template_vals, company
        )
        for i, group in enumerate(groups):
            tmpl_parent = template_vals[i][0].parent_id
            if tmpl_parent:
                group.parent_id = groups.filtered(
                    lambda r: r.code_prefix == tmpl_parent.code_prefix
                )
        return groups

    def _load(self, sale_tax_rate, purchase_tax_rate, company):
        ctx = dict(self.env.context, lang=company.partner_id.lang)
        self.with_context(ctx)._generate_account_groups(company)
        return super()._load(sale_tax_rate, purchase_tax_rate, company)


class AccountTaxRepartitionLineTemplate(models.Model):
    _inherit = "account.tax.repartition.line.template"

    @api.model
    def create(self, vals):
        """
        In order to simplify the tax template xml file we add
        the required 'factor_percent' field for 'base' lines here.
        """
        if vals.get("repartition_type") == "base" and not vals.get("factor_percent"):
            vals["factor_percent"] = 100
        return super().create(vals)
