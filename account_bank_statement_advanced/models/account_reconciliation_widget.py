# Copyright 2009-2019 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class AccountReconciliationWidget(models.AbstractModel):
    _inherit = 'account.reconciliation.widget'

    @api.model
    def get_bank_statement_data(self, bank_statement_ids):
        """
        We have passed the statement lines as negative ids
        when calling the manual_reconcile method.
        We pass these ids in the context for further use by
        the 'get_bank_statement_line_data so that the
        reconciliatin widget receives only the selected subset
        of statement lines.
        """
        if isinstance(bank_statement_ids, int):
            bank_statement_ids = [bank_statement_ids]
        if not bank_statement_ids or bank_statement_ids[-1] > 0:
            return super().get_bank_statement_data(bank_statement_ids)
        for i, st_id in enumerate(bank_statement_ids[::-1]):
            if st_id > 0:
                break
        cnt = len(bank_statement_ids)
        st_ids = bank_statement_ids[:cnt - i]
        st_line_ids = bank_statement_ids[-i:]
        st_line_ids = [-x for x in st_line_ids]
        return super(
            AccountReconciliationWidget,
            self.with_context(dict(self.env.context, st_line_ids=st_line_ids))
        ).get_bank_statement_data(st_ids)

    @api.model
    def get_bank_statement_line_data(self, st_line_ids, excluded_ids=None):
        if self.env.context.get('st_line_ids'):
            st_line_ids = self.env.context['st_line_ids']
        return super().get_bank_statement_line_data(
            st_line_ids, excluded_ids=excluded_ids)
