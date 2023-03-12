.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

=======================================================
Customer invoices with Belgian structured communication
=======================================================

This module is an alternative to the 'l10n_be_invoice_bba' module of the standard addons.

Difference with this module:

- Configurable per partner

  The communication type and algorithm can be configured on the partner records thereby allowing
  to use other payment references for e.g. foreign customers or customise the payment reference for
  different customer segments.

- Localisation module

  This module has no dependency on a localisation module (no dependency on 'l10n_be')
  and hence can be installed with other localisation modules.

- Customisation capabilities

  The code has been designed to facilitate customisation by IT specialists with Odoo programming skills,
  e.g. to avoid duplicate structured communications (on customer invoices, sale orders, ...)
  or to use your own algorithm.
