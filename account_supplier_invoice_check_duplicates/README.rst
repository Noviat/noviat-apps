.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

===============================
Vendor Bills - Check duplicates
===============================

This module changes the standard Odoo logic to prevent posting two times the same vendor bill.
The standard logic is too restrictive (blocking) for certain use cases and too permissive for other use cases.

Usage
=====

By default a duplicate is detected when there is already an open or paid invoice
with the same vendor and the same vendor bill number ('Reference' field)

In case no vendor bill number has been encoded extra checks are added to detect duplicates :
- same date
- same amount

The duplicate checking can be bypassed via the 'Force Encoding' flag.

Parameters
==========

``account_supplier_invoice_check_duplicates.payment_state`` *boolean* (Default: ``True``)

    With this parameter activated, the duplicated check will only look into the non-paid invoices

``account_supplier_invoice_check_duplicates.payment_reference`` *boolean* (Default: ``False``)

    With this parameter activated, the duplicated check will include a check on the payment reference
      - In case the vendor bill has a reference, it will check on both.
      - In case the vendor bill has no reference, it will check only on payment reference.

Technical
=========

The logic around the checks done can be customized via the *_get_duplicated_supplier_invoice_domain* or
*_get_duplicated_supplier_invoice_domain_extra* method.

Known issues / Roadmap
======================

  - Add the parameters into the Configuration Settings wizard.
