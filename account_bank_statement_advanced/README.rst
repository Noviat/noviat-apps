.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

=======================
Advanced Bank Statement
=======================

This module extends the standard account_bank_statement object for
better scalability and e-banking support.

This module adds:
-----------------
- value date
- batch payments
- Payment Reference field to support ISO 20022 EndToEndReference
  (simple or batch. detail) or PaymentInformationIdentification (batch)
- Creditor Reference fields to support ISO 20022 CdtrRefInf
  (e.g. structured communication & communication type)
- bank statement line views with reconcile on selected lines
- bank statements balances report

Installation
============

The reconcile on selected lines requires one of the following modules to be installed:

- account_accountant (Odoo Enterprise)
- account_reconciliation_widget (https://github.com/OCA/account-reconcile/tree/14.0)

