# Copyright 2009-2023 Noviat.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
from odoo import fields, models, tools


class AccountJournalMultiCompanyList(models.Model):
    """
    Class to allow selection of Journals in target companies
    without hitting access violations.
    """

    _name = "account.journal.multi.company.list"
    _description = "SQL view on Journals"
    _auto = False

    name = fields.Char()
    code = fields.Char()
    type = fields.Char()
    company_id = fields.Char()

    def init(self):
        tools.drop_view_if_exists(self._cr, "company_list_view")
        self._cr.execute(
            """
            CREATE OR REPLACE VIEW account_journal_multi_company_list AS (
            SELECT
                id, name, code, type, company_id::text AS company_id
            FROM
                account_journal
            )
        """
        )

    def name_get(self):
        lang = self.env.context["lang"]
        return [(j.id, " - ".join([j.code, j.name[lang]])) for j in self]
