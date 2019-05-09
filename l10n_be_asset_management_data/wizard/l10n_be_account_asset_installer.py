# Copyright 2009-2019 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import csv
import io
import os

from odoo import api, fields, models, _
from odoo.modules.module import ad_paths


class L10nBeAccountAssetInstaller(models.TransientModel):
    _name = 'l10n.be.account.asset.installer'
    _inherit = 'res.config.installer'

    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company', required=True,
        default=lambda self: self.env.user.company_id)
    asset_lang = fields.Selection(
       selection='_selection_asset_lang',
       string='Language', required=True,
       default=lambda self: self._default_asset_lang())

    @api.model
    def _selection_asset_lang(self):
        return [('en', _('English')),
                ('fr', _('French')),
                ('nl', _('Dutch'))]

    @api.model
    def _default_asset_lang(self):
        lang = self.env.user.lang[:2]
        if lang not in ['fr', 'nl']:
            lang = 'en'
        return lang

    @api.model
    def _load_asset(self, row):
        name = row['name_%s' % self.asset_lang]
        vals = {'name': name}
        code = row['code']
        code_i = self.lookup.get(code)
        if isinstance(code_i, int):
            self.view_assets[code_i].write(vals)
        else:
            if row['parent_code']:
                parent_asset = self.view_assets[
                    self.lookup[row['parent_code']]]
                vals['parent_id'] = parent_asset.id
            vals.update({
                'code': row['code'],
                'type': 'view',
                'company_id': self.company_id.id,
                'state': 'open',
                'purchase_value': 0.0,
            })
            a = self.env['account.asset'].create(vals)
            i = len(self.view_assets)
            self.view_assets += a
            self.lookup[row['code']] = i

    @api.multi
    def execute(self):
        res = super().execute()
        self.view_assets = self.env['account.asset'].search(
            [('type', '=', 'view'),
             ('company_id', '=', self.company_id.id)])
        self.lookup = {}
        for i, a in enumerate(self.view_assets):
            self.lookup[a.code] = i
        module = __name__.split('addons.')[1].split('.')[0]
        for adp in ad_paths:
            module_path = adp + os.sep + module
            if os.path.isdir(module_path):
                break
        fqn = '{}/data/be_view_assets.csv'.format(module_path)
        with io.open(fqn, mode='r', encoding='Windows-1252') as f:
            assets = csv.DictReader(f, delimiter=';')
            for row in assets:
                if row['code']:
                    self._load_asset(row)
        return res
