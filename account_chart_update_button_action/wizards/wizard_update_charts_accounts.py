# Copyright 2009-2023 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class WizardUpdateChartsAccounts(models.TransientModel):
    _inherit = "wizard.update.charts.accounts"

    def action_remove_all_new(self):
        self.tax_ids.filtered(lambda x: x.type == "new").unlink()
        return self._reopen()

    def action_remove_all_updated(self):
        self.tax_ids.filtered(lambda x: x.type == "updated").unlink()
        return self._reopen()

    def action_remove_all_deleted(self):
        self.tax_ids.filtered(lambda x: x.type == "deleted").unlink()
        return self._reopen()
