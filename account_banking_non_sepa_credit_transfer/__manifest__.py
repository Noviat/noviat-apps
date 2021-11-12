# Copyright 2009-2021 Noviat
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Non SEPA Credit Transfer - Clearing System Member Identification",
    "version": "13.0.1.0.0",
    "license": "AGPL-3",
    "author": "Noviat",
    "website": "http://www.noviat.com",
    "category": "Accounting & Finance",
    "summary": "Non SEPA Credit Transfer - Clearing System Member Identification",
    "depends": ["account_banking_sepa_credit_transfer"],
    "data": [
        "data/res_country_data.xml",
        "views/res_bank_views.xml",
        "views/res_country_views.xml",
    ],
    "installable": True,
}
