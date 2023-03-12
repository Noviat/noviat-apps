# Copyright 2009-2023 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Open Journal Items per partner",
    "version": "15.0.1.0.0",
    "license": "AGPL-3",
    "author": "Noviat",
    "website": "https://www.noviat.com/",
    "category": "Accounting & Finance",
    "summary": "Open Journal Items per partner at a given date",
    "depends": ["account", "report_xlsx_helper"],
    "data": [
        "security/ir.model.access.csv",
        "wizards/wiz_partner_open_items.xml",
        "views/menu.xml",
    ],
    "installable": True,
}
