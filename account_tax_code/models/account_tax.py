# Copyright 2009-2024 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, fields, models


class AccountTax(models.Model):
    _inherit = "account.tax"

    code = fields.Char()

    _sql_constraints = [
        (
            "code_company_uniq",
            "unique (code,company_id)",
            "The code of the Tax must be unique per company !",
        )
    ]

    def _compute_display_name(self):
        if self.env.context.get("append_code_to_tax_name"):
            for rec in self:
                rec.display_name = (rec.code and f"[{rec.code}]" or "") + f"{rec.name}"
        else:
            for rec in self:
                rec.display_name = rec.name

    def copy(self, default=None):
        if self.code:
            code = _("%s (Copy)") % (self.code or "")
        else:
            code = self.code

        default = dict(default or {}, code=code)
        return super().copy(default=default)
