# Copyright 2009-2020 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


def update_country_state_refs(cr):
    """
    pre_init_hook:
    update res.country.state ir_model_data entries
    for migrations from 12.0 l10n_be_coa_multilang module
    """
    old = "l10n_be_coa_multilang"
    new = "l10n_be_country_state"
    model = "res.country.state"
    cr.execute(
        "UPDATE ir_model_data SET module = %s " "WHERE module = %s AND model = %s",
        (new, old, model),
    )
