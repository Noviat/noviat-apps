# Copyright 2009-2023 Noviat
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from lxml import etree

from odoo import api, models


class IrUiView(models.Model):
    """
    We remove the "decoration-uf" in the 'arch_db' field constraint
    so that we dont have to patch the rng file
    or adapt the logic of the _check_xml constraint.
    """

    _inherit = "ir.ui.view"

    @api.constrains("arch_db")
    def _check_xml(self):
        self = self.with_context(check_xml=True)
        return super()._check_xml()

    def _get_combined_arch(self):
        res = super()._get_combined_arch()
        if self.env.context.get("check_xml"):
            source = etree.tostring(res)
            if b"decoration-uf" in source:
                source = self._remove_decoration_uf(source)
                res = etree.fromstring(source)
        return res

    def _remove_decoration_uf(self, source):
        if b"decoration-uf" in source:
            s0, s1 = source.split(b"decoration-uf", 1)
            s2 = s1.split(b'"', 2)[2]
            return s0 + self._remove_decoration_uf(s2)
        else:
            return source
