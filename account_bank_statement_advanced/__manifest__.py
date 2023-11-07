# Copyright 2009-2023 Noviat
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

{
    "name": "Advanced Bank Statement",
    "version": "16.0.1.0.0",
    "license": "LGPL-3",
    "author": "Noviat",
    "website": "https://www.noviat.com/",
    "category": "Accounting & Finance",
    "summary": "Advanced Bank Statement",
    "depends": [
        "base_iban",
        "account_usability",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/account_bank_statement_line_global_security.xml",
        "data/ir_sequence_data.xml",
        "views/account_bank_statement_views.xml",
        "views/account_bank_statement_line_views.xml",
        "views/account_bank_statement_line_global_views.xml",
        "views/report_statement_balance_report.xml",
        "wizards/bank_statement_balance_print.xml",
        "wizards/bank_statement_automatic_reconcile_result_view.xml",
        "report/statement_balance_report.xml",
        "views/menu.xml",
    ],
    "pre_init_hook": "pre_init_hook",
    "installable": True,
}
