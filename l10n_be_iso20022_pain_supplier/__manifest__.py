# Copyright 2009-2021 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Payment Order with Belgian structured communication",
    "version": "14.0.1.0.0",
    "category": "Accounting & Finance",
    "website": "https://www.noviat.com",
    "author": "Noviat",
    "license": "AGPL-3",
    "excludes": ["l10n_be_iso20022_pain"],
    "depends": ["account_banking_sepa_credit_transfer", "l10n_be_invoice_bba_supplier"],
    "pre_init_hook": "pre_init_hook",
    "installable": True,
    "auto_install": True,
}
