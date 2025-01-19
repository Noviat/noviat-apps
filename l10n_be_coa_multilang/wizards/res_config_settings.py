# Copyright 2009-2024 Noviat
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    def execute(self):
        if (
            self.chart_template
            and self.chart_template == "be_coa"
            and not self.has_chart_of_accounts
        ):
            todo = "l10n_be_coa_multilang.l10n_be_coa_multilang_config_action_todo"
        else:
            todo = False
        res = super().execute()
        if todo:
            todo = "l10n_be_coa_multilang.l10n_be_coa_multilang_config_action_todo"
            return self.env.ref(todo).action_launch()
        return res
