.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

=============================
Intrastat reports for Belgium
=============================


This module implements the Belgian Intrastat reporting.

The report can be reviewed and corrected where needed before
the creation of the XML file for the online declaration (ONEGATE).

More information can be found on the National Bank website:
https://www.nbb.be/en/statistics/foreign-trade


Installation
============

WARNING:

This module conflicts with the module *report_intrastat* and *l10n_be_intrastat*
from the official addons.
If you have already installed these modules,
you should uninstall them before installing this module.

We recommend to also install the OCA stock_picking_invoice_link module,
Cf. https://github.com/OCA/stock-logistics-workflow.
This modules establishes a link between invoice lines and stock pickings.
When this module is installed the declaration will take into account refunds created via return pickings.

Multi-company setup
-------------------

Please ensure to set the Default Company of the OdooBot user to the company
for which you are installing this localization module.
Not doing so may result in a conflict with other localization modules (e.g. l10n_fr_intrastat_product).


Configuration wizard to load intrastat codes:
---------------------------------------------

The module comes with a configuration wizard that allows you to load the intrastat codes into the database.
The intrastat codes are available in 4 languages : english, dutch, french, german.

If your databases has been configured to support multiple languages, you should execute the wizard
for each language that you want to offer to the users.


Configuration
=============

* Accounting -> Configuration -> Settings

  - Arrivals : Exempt, Standard or Extended
  - Dispatches : Exempt, Standard or Extended
  - Default Intrastat Region
  - Default Intrastat Transaction
  - Default Intrastat Transport Mode (Extended Declaration)
  - Default Intrastat Incoterm (Extended Declaration)

* Warehouse

  Intrastat Region to cope with warehouses in different regions

* Inrastat Codes, Supplementary Units, Transaction Tyoes, Transport Modes, Regions

  Cf. menu Accounting / Configuration / Intrastat

  The configuration data is loaded when installing the module.
  We recommend to not change these settings.

  A configuration wizard also allows to update the Intrastat Codes so that you can easily
  synchronise your Odoo instance with the latest list of codes supplied with this module
  (an update is published on an annual basis by the Belgian National Bank).

* Product

  You can define a default Intrastat Code on the Product or the Product Category.

* Fiscal Positions

  Check your Fiscal Positions and set the 'Intrastat' flag for transactations that
  must be included in the intrastat declaration.
  We recommend to set the 'VAT required' flag on the 'Intra Community Regime' Fiscal Position.
  
  If you have B2C customers or B2B customers which are not subject to VAT you can create a
  'Intra Community Regime NA' Fiscal Position on which the 'Intrastat' flag is set while the 'VAT required'
  flag has been turned off.

* Partner

  Ensure that your B2B Customer records have a valid VAT Number.
  
  Consider the use of the OCA **account_fiscal_position_vat_check module** to enforce the correct setting. 
  Cf. https://github.com/OCA/account-financial-tools.
  
  If you have not set the 'Detect Automatically' flan on your Intra Community Fiscal Position(s) than you should
  set the 'Intra Community Regime NA' Fiscal Position on B2B customer records who are not subject to VAT.
  Alternatively you can also set 'NA' in the VAT number field of such a customer.


Known issues / Roadmap
======================

- The current version of the Belgian Intrastat reporting module is only based on invoices.
  Since associated stock moves are not taken into consideration, it is possible that manual
  corrections are required, e.g.
  Product movements without invoices are not included in the current version
  of this module and must be added manually to the report lines
  before generating the ONEGATE XML declaration.

- Refunds on invoices within the same reporting period are deducted from the declaration lines.
  No controls are executed on Refunds that are not linked to an invoice
  in the same reporting period.
  Such Refunds are reported under the default transaction code for refunds.
  It is recommend to manually set the correct transaction code while Credit Notes
  are created.

- The current version of the Belgian Intrastat reporting module does not perform a
  cross-check with the VAT declaration.

Assistance
----------

Contact info@noviat.com for help with the implementation of this module.
