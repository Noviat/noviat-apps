# Copyright 2009-2023 Noviat
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class Base(models.AbstractModel):
    _inherit = "base"

    @api.model
    def _get_view(self, view_id=None, view_type="form", **options):
        """
        Keep 'readonly' nature when opening account.move.line form
        """
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == "form" and self.env.context.get(
            "account_move_line_search_extension", False
        ):
            form = arch.xpath("/form")
            for node in form:
                node.set("edit", "false")
                node.set("create", "false")
                node.set("delete", "false")
        return arch, view
