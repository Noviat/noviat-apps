# Copyright 2009-2023 Noviat.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

{
    "name": "Account_intercompany_rules extensions",
    "version": "16.0.1.0.0",
    "license": "LGPL-3",
    "author": "Noviat",
    "website": "https://www.noviat.com/",
    "category": "Accounting & Finance",
    "complexity": "normal",
    "summary": "Enhance 'account_inter_company_rules' inter-company invoicing",
    "depends": [
        "account_inter_company_rules",
    ],
    "data": [
        "security/account_reinvoice_multi_company_security.xml",
        "security/ir.model.access.csv",
        "views/account_move_views.xml",
        "views/account_reinvoice_journal_mapping_multi_company_views.xml",
        "views/menuitem.xml",
    ],
    "installable": True,
}
