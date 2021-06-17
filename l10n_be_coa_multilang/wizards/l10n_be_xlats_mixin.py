# Copyright 2009-2020 Noviat
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, models


class L10nBeXlatsMixin(models.AbstractModel):
    _name = "l10n.be.xlats.mixin"
    _description = "Mixin to bypass '_' limitation"

    def _(self, src):
        """
        The standard "_" method does not allow to make context specific translations.
        As soon as a 'code' term is already translated by another module,
        the term in the po file of this module will not be loaded.
        We use the "model_terms" as a bypass for this limitation in the Odoo framework
        and fall back to the standard "_" method for missing translations.
        """
        dom = [
            ("type", "=", "model_terms"),
            ("name", "=", "ir.actions.report,help"),
            ("module", "=", "l10n_be_coa_multilang"),
            ("lang", "=", self.env.context.get("lang", "en_US")),
            ("src", "=", src),
        ]
        val = self.env["ir.translation"].search(dom)
        val = val and val[0].value or _(src)
        return val
