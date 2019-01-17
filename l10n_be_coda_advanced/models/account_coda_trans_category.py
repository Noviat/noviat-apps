# Copyright 2009-2019 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountCodaTransCategory(models.Model):
    _name = 'account.coda.trans.category'
    _description = 'CODA transaction category'
    _order = 'category'

    name = fields.Char(compute='_compute_name', readonly=True)
    category = fields.Char(
        string='Transaction Category', size=3, required=True)
    description = fields.Char(string='Description', translate=True)

    @api.one
    @api.depends('category', 'description')
    def _compute_name(self):
        name = self.category
        if self.description:
            name += ' ' + self.description
        self.name = len(name) > 55 \
            and name[:55] + '...' \
            or name

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        recs = self.browse()
        if name:
            recs = self.search(
                [('category', 'like', name)] + args, limit=limit)
        if not recs:
            recs = self.search(
                [('description', operator, name)] + args, limit=limit)
        return [(r.id, r.name) for r in recs]

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        if not args:
            args = []
        new_args = []
        for arg in args:
            if len(arg) == 3 and arg[0] == 'name':
                new_arg = ['|',
                           ('category', arg[1], arg[2]),
                           ('description', arg[1], arg[2])]
                new_args += new_arg
            else:
                new_args.append(arg)
        return super().search(
            new_args, offset=offset, limit=limit, order=order, count=count)
