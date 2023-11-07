# Copyright 2009-2023 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class AccountReinvoiceJournalMappingMultiCompany(models.Model):
    _name = "account.reinvoice.journal.mapping.multi.company"
    _description = "Reinvoice Journal Mapping multi-company"
    _order = "sequence,target_company"

    sequence = fields.Integer(required=True, default=10)
    journal_out_ids = fields.Many2many(
        comodel_name="account.journal",
        string="Output Journals",
        relation="journal_reinvoice_mapping_multi_company_rel",
        domain="[('company_id', '=', company_id)," " ('type', '=', 'sale')]",
        required=True,
    )
    target_company = fields.Selection(
        selection="_selection_target_company", required=True
    )
    target_journal_id = fields.Many2one(
        comodel_name="account.journal.multi.company.list",
        domain="[('type', '=', 'purchase')," " ('company_id', '=', target_company)]",
        required=True,
    )
    target_refund_journal_id = fields.Many2one(
        comodel_name="account.journal.multi.company.list",
        domain="[('type', '=', 'purchase')," " ('company_id', '=', target_company)]",
        required=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        readonly=True,
        default=lambda self: self.env.company,
    )

    @api.model
    def _selection_target_company(self):
        domain = self._selection_target_company_domain()
        companies = self.env["res.company"].sudo().search(domain)
        return [(str(c.id), c.name) for c in companies]

    def _selection_target_company_domain(self):
        return [("id", "!=", self.env.company.id)]

    @api.onchange("target_company")
    def _onchange_target_company(self):
        if self.target_company:
            self.target_journal_id = False
            self.target_refund_journal_id = False
