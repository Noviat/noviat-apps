# Copyright 2009-2023 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Asset Management - Belgian reporting structure",
    "version": "15.0.1.0.0",
    "license": "AGPL-3",
    "author": "Noviat",
    "website": "https://www.noviat.com/",
    "category": "Accounting & Finance",
    "complexity": "normal",
    "summary": "Asset Management - Belgian reporting structure",
    "depends": ["account_asset_management"],
    "data": [
        "security/ir.model.access.csv",
        "wizards/l10n_be_account_asset_installer.xml",
    ],
    "installable": True,
}
