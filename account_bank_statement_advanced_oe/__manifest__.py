# Copyright 2009-2023 Noviat
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

{
    "name": "Advanced Bank Statement - Enterprise Edition",
    "version": "16.0.1.0.0",
    "license": "LGPL-3",
    "author": "Noviat",
    "website": "https://www.noviat.com/",
    "category": "Accounting & Finance",
    "summary": "Advanced Bank Statement",
    "depends": [
        "account_bank_statement_advanced",
        "account_accountant",
        "base_view_inheritance_extension",
    ],
    "data": [
        "views/account_bank_statement_views.xml",
    ],
    "installable": True,
    "auto_install": True,
}
