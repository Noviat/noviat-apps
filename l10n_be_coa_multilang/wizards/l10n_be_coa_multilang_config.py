# Copyright 2009-2024 Noviat
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class L10nBeCoaMultilangConfig(models.TransientModel):
    """
    - load nl & fr languages
    - update company_id country to Belgium
    """

    _inherit = "res.config"
    _name = "l10n.be.coa.multilang.config"
    _description = "l10n.be.coa.multilang setup wizard"

    load_nl_BE = fields.Boolean(string="Load Dutch (nl_BE) Translation")
    load_fr_BE = fields.Boolean(string="Load French (fr_BE) Translation")
    load_nl_NL = fields.Boolean(string="Load Dutch (nl_NL) Translation")
    load_fr_FR = fields.Boolean(string="Load French (fr_FR) Translation")
    monolang_coa = fields.Boolean(
        string="Monolingual Chart of Accounts",
        default=lambda self: self._default_monolang_coa(),
        help="If checked, the General Account will become "
        "a monolingual field. \n"
        "This behaviour can be changed afterwards via "
        "Settings -> Configuration -> Accounting",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )

    @api.model
    def _default_monolang_coa(self):
        translate = self.env["account.account"]._fields["name"].translate
        name = "l10n_account_translate_off"
        module = self.env["ir.module.module"].search([("name", "=", name)])
        if not module:
            raise UserError(
                _(
                    "Module '%s' is not available "
                    "in the addons path. "
                    "\nPlease download this module from 'apps.odoo.com'."
                )
                % name
            )
        return not translate and True or False

    @api.onchange("load_nl_BE", "load_fr_BE", "load_nl_NL", "load_fr_FR")
    def _onchange_load_lang(self):
        if self.load_nl_BE or self.load_fr_BE:
            self.load_nl_NL = False
            self.load_fr_FR = False
        elif self.load_nl_NL or self.load_fr_FR:
            self.load_nl_BE = False
            self.load_fr_BE = False

    def execute(self):
        if self.monolang_coa:
            to_install = self.env["ir.module.module"].search(
                [("name", "=", "l10n_account_translate_off")]
            )
            if to_install.state != "installed":
                to_install.button_immediate_install()
        else:
            to_install = self.env["ir.module.module"].search(
                [("name", "=", "l10n_multilang")]
            )
            if to_install.state != "installed":
                to_install.button_immediate_install()
            to_uninstall = self.env["ir.module.module"].search(
                [("name", "=", "l10n_account_translate_off")]
            )
            if to_uninstall.state == "installed":
                to_uninstall.button_immediate_uninstall()

        # Update company country, this is required for auto-configuration
        # of the legal financial reportscheme.
        be = self.env.ref("base.be")
        if self.company_id.country_id != be:
            self.company_id.country_id = be

        # load languages
        langs = (
            (self.load_nl_BE and ["nl_BE"] or [])
            + (self.load_fr_BE and ["fr_BE"] or [])
            + (self.load_nl_NL and ["nl_NL"] or [])
            + (self.load_fr_FR and ["fr_FR"] or [])
        )

        if langs:
            installed_modules = self.env["ir.module.module"].search(
                [("state", "=", "installed")]
            )
            for lang in langs:
                lang_rs = (
                    self.env["res.lang"]
                    .with_context(active_test=False)
                    .search([("code", "=", lang)])
                )
                if not lang_rs.active:
                    self.env["res.lang"]._activate_lang(lang)
                    installed_modules._update_translations(filter_lang=lang)

        # update the entries in the BNB/NBB legal report scheme
        upd_wiz = self.env["l10n.be.update.be.reportscheme"]
        note = upd_wiz.with_context(
            l10n_be_coa_multilang_config=True
        )._update_be_reportscheme(self.company_id)
        if note:
            wiz = upd_wiz.create({"note": note})
            module = __name__.split("addons.")[1].split(".")[0]
            result_view = "l10n_be_update_be_reportscheme_view_form_result"
            view = self.env.ref(f"{module}.{result_view}")
            return {
                "name": _("Results"),
                "res_id": wiz.id,
                "view_type": "form",
                "view_mode": "form",
                "res_model": "l10n.be.update.be.reportscheme",
                "view_id": False,
                "target": "new",
                "views": [(view.id, "form")],
                "type": "ir.actions.act_window",
            }
        else:
            return {}
