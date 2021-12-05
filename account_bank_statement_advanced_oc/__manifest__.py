# Copyright 2009-2021 Noviat
# License AGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

{
    "name": "Advanced Bank Statement on Odoo Community",
    "version": "14.0.1.0.0",
    "category": "Hidden",
    "license": "LGPL-3",
    "author": "Noviat",
    "website": "http://www.noviat.com",
    "summary": "Advanced Bank Statement on Odoo Enterprise",
    "depends": ["account_reconciliation_widget", "account_bank_statement_advanced"],
    "excludes": ["account_accountant"],
    "data": [
        "views/account_bank_statement_views.xml",
    ],
    "installable": True,
    "auto_install": True,
}
