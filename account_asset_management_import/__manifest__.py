# Copyright 2009-2022 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Fixed Assets import",
    "version": "14.0.1.0.0",
    "license": "AGPL-3",
    "author": "Noviat",
    "website": "https://www.noviat.com/",
    "category": "Accounting & Finance",
    "depends": ["account_asset_management"],
    "external_dependencies": {"python": ["xlrd"]},
    "data": ["security/ir.model.access.csv", "wizards/fixed_asset_import_views.xml"],
    "installable": True,
}
