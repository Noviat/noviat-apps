# Copyright 2021 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, models


class IntrastatProductDeclaration(models.Model):
    _inherit = "intrastat.product.declaration"

    def _get_weight_and_supplunits(self, inv_line, hs_code):
        """
        Retrieve weight from config.session if applicable.
        For these cases we don't perform UOM quantity conversions.
        """
        if not inv_line.config_session_id:
            return super()._get_weight_and_supplunits(inv_line, hs_code)
        suppl_unit_qty = inv_line.quantity
        weight = inv_line.config_session_id.weight * inv_line.quantity
        if not weight:
            line_notes = [
                _("Missing weight on Configuration Session %s")
                % (inv_line.config_session_id.name,)
            ]
            self._note += self._format_line_note(inv_line, self._line_nbr, line_notes)
        return weight, suppl_unit_qty
