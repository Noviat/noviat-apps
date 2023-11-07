# Copyright 2009-2023 Noviat
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AccountReportLine(models.Model):
    _name = "account.report.line"
    _inherit = ["account.report.line", "l10n.be.chart.common"]
