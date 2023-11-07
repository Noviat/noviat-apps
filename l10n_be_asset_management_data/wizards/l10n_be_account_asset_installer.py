# Copyright 2009-2023 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import csv
import os

from odoo import _, api, fields, models

from odoo.addons import __path__ as ad_paths


class L10nBeAccountAssetInstaller(models.TransientModel):
    _name = "l10n.be.account.asset.installer"
    _inherit = "res.config.installer"
    _description = "Load Belgian Financial Asset reporting structure"

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
    )
    asset_lang = fields.Selection(
        selection="_selection_asset_lang",
        string="Language",
        required=True,
        default=lambda self: self._default_asset_lang(),
    )

    @api.model
    def _selection_asset_lang(self):
        return [("en", _("English")), ("fr", _("French")), ("nl", _("Dutch"))]

    @api.model
    def _default_asset_lang(self):
        lang = self.env.user.lang[:2]
        if lang not in ["fr", "nl"]:
            lang = "en"
        return lang

    @api.model
    def _load_asset_group(self, row, lookup, asset_groups):
        name = row["name_%s" % self.asset_lang]
        vals = {"name": name}
        code = row["code"]
        code_i = lookup.get(code)
        if isinstance(code_i, int):
            asset_groups[code_i].write(vals)
        else:
            if row["parent_code"]:
                parent_asset_group = asset_groups[lookup[row["parent_code"]]]
                vals["parent_id"] = parent_asset_group.id
            vals.update({"code": row["code"], "company_id": self.company_id.id})
            ag = self.env["account.asset.group"].create(vals)
            i = len(asset_groups)
            asset_groups += ag
            lookup[row["code"]] = i
        return asset_groups

    def execute(self):
        res = super().execute()
        asset_groups = self.env["account.asset.group"].search(
            [("company_id", "=", self.company_id.id)]
        )
        lookup = {}
        for i, a in enumerate(asset_groups):
            lookup[a.code] = i
        module = __name__.split("addons.")[1].split(".")[0]
        for adp in ad_paths:
            module_path = adp + os.sep + module
            if os.path.isdir(module_path):
                break
        fqn = "{}/static/data/be_view_assets.csv".format(module_path)
        with open(fqn, encoding="Windows-1252") as f:
            csv_data = csv.DictReader(f, delimiter=";")
            for row in csv_data:
                if row["code"]:
                    asset_groups = self._load_asset_group(row, lookup, asset_groups)
        return res
