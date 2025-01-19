.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

========================================
Bank Transaction Journal Entry Numbering
========================================

This module allows to define the numbering scheme for bank transactions.

Configuration
=============

Select the numbering option via the Financial Journal Advanced Settings:

- Journal Based : use Journal Sequence
- Statement Based : use Statement Name

|

e.g:

The accounting entries created for the transations in statement BNP95-21-010 will be named as BNP95-21-010/seq (seq = transaction sequence number)

The following use cases are supported when setting 'Statement' Based:

1) Manual encoding of transactions within the bank statement form view.

This module depends upon the module 'account_bank_statement_advanced'.
When you encode bank transactions via this form view the entry ename will be statement name will be
'statement name/sequence'.

When you encode the transactions manually via the Odoo standard transactions kanban or list views the
standard journal entry naming logic will be used.

2) Bank Statement import

When importing digital statements provided by the bank (e.g. camt, coda, cfonb) you can use this
module to allow the import program to create entry names starting with the statement name.   


Credits
=======

Contributors
------------

* Luc De Meyer <luc.demeyer@noviat.com>
