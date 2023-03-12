# Copyright 2009-2023 Noviat
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Advanced CODA processing on Odoo Community",
    "version": "15.0.1.0.0",
    "category": "Hidden",
    "license": "AGPL-3",
    "author": "Noviat",
    "website": "https://www.noviat.com/",
    "summary": "Advanced CODA processing on Odoo Community",
    "depends": ["account_bank_statement_advanced_oc", "l10n_be_coda_advanced"],
    "excludes": ["account_accountant"],
    "data": [
        "views/account_bank_statement_views.xml",
    ],
    "installable": True,
    "auto_install": True,
}
