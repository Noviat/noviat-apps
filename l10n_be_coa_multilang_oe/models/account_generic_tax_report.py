# Copyright 2009-2023 Noviat
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import _, models
from odoo.exceptions import RedirectWarning


class AccountGenericTaxReport(models.AbstractModel):
    _inherit = "account.generic.tax.report"

    def get_report_informations(self, options):
        info = super().get_report_informations(options)
        if (
            info["options"].get("tax_report")
            == self.env.ref("l10n_be_coa_multilang.be_vat_report").id
        ):
            button = _("Periodical VAT Declaration")
            msg = (
                _("Please use the following menu entry")
                + ":\n"
                + _("Belgian Statements and Reports")
                + r" \ "
                + button
            )
            action = self.env.ref(
                "l10n_be_coa_multilang.l10n_be_vat_declaration_action"
            )
            raise RedirectWarning(msg, action.id, _("Go to the Belgian ") + button)
        return info
