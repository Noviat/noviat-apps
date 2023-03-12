# Copyright 2009-2023 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "account_asset_management on Odoo Enterprise",
    "summary": "Adds 'Assets' to the 'Accounting' menu",
    "version": "15.0.1.0.0",
    "author": "Noviat",
    "website": "https://www.noviat.com/",
    "category": "Hidden",
    "license": "AGPL-3",
    "depends": ["account_asset_management", "account_accountant"],
    "data": ["views/account_asset_menu.xml"],
    "installable": True,
    "auto_install": True,
}
