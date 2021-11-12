# Copyright 2009-2020 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Belgium - Partner Bank BBAN/IBAN conversion",
    "version": "13.0.1.0.0",
    "license": "AGPL-3",
    "author": "Noviat, Odoo Community Association (OCA)",
    "category": "Localization",
    "summary": "Belgium - Partner Bank BBAN/IBAN conversion",
    "depends": ["base_iban"],
    "data": ["data/res_bank_data.xml", "views/res_bank_views.xml"],
    "installable": True,
    "pre_init_hook": "update_bank_refs",
}
