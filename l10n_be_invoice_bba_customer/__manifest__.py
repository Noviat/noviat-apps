# Copyright 2009-2023 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Customer Invoices with Belgian structured communication",
    "version": "15.0.1.0.0",
    "category": "Accounting & Finance",
    "website": "https://www.noviat.com/",
    "author": "Noviat",
    "license": "AGPL-3",
    "data": ["views/res_partner_views.xml"],
    "depends": ["account"],
    "excludes": ["l10n_be_invoice_bba"],
    "installable": True,
}
