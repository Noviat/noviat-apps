# Copyright 2009-2021 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from lxml import etree

from odoo import models
from odoo.tools import safe_eval

_logger = logging.getLogger(__name__)


class IrUiView(models.Model):
    _inherit = "ir.ui.view"

    def read_combined(self, fields=None):
        res = super().read_combined(fields=fields)
        if (
            self.model
            and self.model == "account.move"
            and self.type == "form"
            and not self.inherit_id
        ):
            dims = self.env["account.move.line"]._get_all_analytic_dimensions(
                self.env.company.id
            )
            dims = self._check_analytic_dimension_ui_modifier_fields(dims)
            res["arch"] = self._enforce_analytic_dimensions(
                self.model, res["arch"], dims
            )
        return res

    def _check_analytic_dimension_ui_modifier_fields(self, dims):
        """
        For every analytic dimension a {dim}_ui_modifier field is
        created dynamically (cf. account_move_line.py, _build_model method.
        The _build_model is executed when starting Odoo, hence hese fields
        have not been created for dimensions added via the User Interface
        after starting Odoo.
        We remove these dims to avoid a stack trace because of missing fields.
        TODO: figure out how to add these fields dynamically to the registry.
        """
        dims = [
            dim
            for dim in dims
            if hasattr(self.env["account.move.line"], "{}_ui_modifier".format(dim))
        ]
        return dims

    def _enforce_analytic_dimensions(self, model, arch, dims):
        attrs = (
            "{'required': [('%(dim)s_ui_modifier', '=', 'required')]"
            ", 'readonly': [('%(dim)s_ui_modifier', '=', 'readonly')]}"
        )
        arch_node = etree.fromstring(arch)
        upd = False
        for lines_fld in ["invoice_line_ids", "line_ids"]:
            expr_xp = "//field[@name='{}']/tree".format(lines_fld)
            fld_nodes = arch_node.xpath(expr_xp)
            if len(fld_nodes) == 1:
                fld_node = fld_nodes[0]
                for dim in dims:
                    expr_dim = "./field[@name='{}']".format(dim)
                    dim_nodes = fld_node.xpath(expr_dim)
                    if len(dim_nodes) == 1:
                        dim_node = dim_nodes[0]
                        upd = True
                        policy_attrs = attrs % {"dim": dim}
                        current_attrs = dim_node.get("attrs")
                        if current_attrs:
                            attrs_dict = safe_eval(current_attrs)
                            attrs_dict.update(safe_eval(policy_attrs))
                            policy_attrs = str(attrs_dict)
                        dim_node.set("attrs", policy_attrs)
                        dim_node.set("force_save", "1")
                        etree.SubElement(
                            fld_node,
                            "field",
                            name="{}_ui_modifier".format(dim),
                            invisible="1",
                        )
        if upd:
            arch = etree.tostring(arch_node, encoding="unicode")
        return arch
