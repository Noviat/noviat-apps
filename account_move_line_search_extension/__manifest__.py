# Copyright 2009-2025 Noviat.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Journal Items Search Extension",
    "version": "16.0.1.1.2",
    "license": "AGPL-3",
    "author": "Noviat",
    "website": "https://www.noviat.com/",
    "category": "Accounting & Finance",
    "depends": ["account"],
    "data": [
        "views/account_move_line_views.xml",
        "views/menu.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "account_move_line_search_extension/static/src/components/**/*",
        ],
    },
    "installable": True,
}
