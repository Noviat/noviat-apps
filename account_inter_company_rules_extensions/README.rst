.. image:: https://img.shields.io/badge/license-LGPL--3-blue.png
   :target: https://www.gnu.org/licenses/lgpl
   :alt: License: LGPL-3

=====================================
account_intercompany_rules extensions
=====================================

This module adds a couple of extra features and controls on top of the
Odoo Enterprise 'account_intercompany_rules' module to facilitate intercompany reinvoicing
when you have several legal entities (Companies) in the same Odoo database.

Configuration
=============

On top of the intercompany invoicing settings introduced by the 'account_intercompany_rules' module
you can also define a Journal mapping table between outgoing and incoming invoices.

Journal Mapping
---------------

Go to **Accounting > Configuration > Multi-Company Configuration > Journal Mapping multi-company**

Use this menu entry to configure the mapping between the Outgoing Sales/Sales Refund Journals and the
incoming Purchase/Purchase Refund Journals in the target company.
