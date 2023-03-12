.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3


======================================================
Supplier payment with Belgian structured communication
======================================================

This module adds the 'supplier_payment_ref_type' field to the supplier invoice.
The digits check of the payment reference will be performed when this field is set to type 'OGM-VCS'.

By doing so also the automated processing of bank statements and outgoing payments can be
optimised for performance, matching and transaction integrity.

Known issues / Roadmap
======================


- Add migration script to migrate the reference type field used for this purpose in previous Odoo versions

- Move this 'supplier_payment_ref_type' field to a generic module to be used as a building block for Belgian
  as well as other (e.g. ISO 11649) structured communication type.
