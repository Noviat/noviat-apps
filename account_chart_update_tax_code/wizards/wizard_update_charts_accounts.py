# Copyright 2009-2023 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class WizardUpdateChartsAccounts(models.TransientModel):
    _inherit = "wizard.update.charts.accounts"

    def _default_tax_matching_ids(self):
        ordered_opts = ["xml_id", "code", "name", "description"]
        return self._get_matching_ids("wizard.tax.matching", ordered_opts)


class WizardTaxMatching(models.TransientModel):
    _inherit = "wizard.tax.matching"

    def _get_matching_selection(self):
        vals = super()._get_matching_selection()
        vals += self._selection_from_files("account.tax.template", ["code"])
        return vals
