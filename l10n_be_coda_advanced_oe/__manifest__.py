# Copyright 2009-2023 Noviat
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

{
    "name": "Advanced CODA processing on Odoo Enterprise",
    "version": "15.0.1.0.0",
    "category": "Hidden",
    "license": "LGPL-3",
    "author": "Noviat",
    "website": "https://www.noviat.com/",
    "summary": "Advanced CODA processing on Odoo Enterprise",
    "depends": ["account_bank_statement_advanced_oe", "l10n_be_coda_advanced"],
    "data": [
        "views/account_bank_statement_views.xml",
    ],
    "installable": True,
    "auto_install": True,
}
