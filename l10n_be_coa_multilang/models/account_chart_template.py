# Copyright 2009-2023 Noviat
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.http import request


class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"
    _order = "name"

    name = fields.Char(translate=True)
    l10n_be_coa_multilang = fields.Boolean(string="Multilang Belgian CoA")

    def try_loading(self, company=False, install_demo=True):
        """
        Update company country, this is required for auto-configuration
        of the legal financial reportscheme.
        """
        if not company:
            if request and hasattr(request, "allowed_company_ids"):
                company = self.env["res.company"].browse(request.allowed_company_ids[0])
            else:
                company = self.env.company
        if self.l10n_be_coa_multilang:
            company.country_id = self.env.ref("base.be")
        return super().try_loading(company=company, install_demo=install_demo)

    def get_countries_posting_at_bank_rec(self):
        rslt = super().get_countries_posting_at_bank_rec()
        rslt.append("BE")
        return rslt

    def _create_records_with_xmlid(self, model, template_vals, company):
        if self.l10n_be_coa_multilang:
            company.country_id = self.env.ref("base.be")
        return super()._create_records_with_xmlid(model, template_vals, company)

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

    @api.model
    def _prepare_transfer_account_template(self, prefix=None):
        """
        Odoo generates 580001 whereas we usually get 580000 as preferred
        value for liquidity account
        """
        vals = super()._prepare_transfer_account_template(prefix=prefix)
        if self.l10n_be_coa_multilang:
            vals.get("code")
            if vals.get("code")[-1] == "1":
                vals["code"] = vals["code"][:-1] + "0"
        return vals
