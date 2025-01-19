# Copyright 2009-2024 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields


def monkey_patch(cls):
    """Return a method decorator to monkey-patch the given class."""

    def decorate(func):
        name = func.__name__
        func.super = getattr(cls, name, None)
        setattr(cls, name, func)
        return func

    return decorate


@monkey_patch(fields.Selection)
def _setup_attrs(self, model_class, name):
    _setup_attrs.super(self, model_class, name)
    if not self._base_fields:
        return

    if model_class._name == "account.journal" and name == "invoice_reference_model":
        for field in self._base_fields:
            if "selection_update_label" in field.args:
                for update in field.args["selection_update_label"]:
                    for i, entry in enumerate(self.selection):
                        if entry[0] == update[0]:
                            self.selection[i] = update
                            break


fields.Selection._setup_attrs = _setup_attrs
