.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

=========================
Import Accounting Entries
=========================

This module adds a button on the ‘Journal Entry’ screen to allow the import of the entry lines from a CSV, XLS  or XLSX file.

Before starting the import a number of sanity checks are performed such as:

- check if partner references are correct
- check if account codes are correct
- check if the sum of debits and credits are balanced

If no issues are found the entry lines will be loaded.
The resulting Journal Entry will be in draft mode to allow a final check before posting the entry.

Usage
=====

Input file column headers
-------------------------

Mandatory Fields
''''''''''''''''

- Account

  Account codes are looked up via exact match.

- Debit

- Credit

Other Fields
''''''''''''

Extra columns can be added and will be processed as long as
the column header is equal to the 'ORM' name of the field.
Both the technical ORM name (e.g. partner_id) or its label (e.g. Partner) can be used.
It is preferred to use the technical name since a same label can be used on different fields
resulting in a risk that the wrong fields is getting updated.
Input fields with no corresponding ORM field will be ignored
unless special support has been added for that field in this
module (or a module that extends the capabilities of this module).

|

For ORM fields of type 'Many2one' you can specify its database ID
or the lookup name (usually the 'name' field but this can be different for
objects where the _rec_name attribute points to another field).

This module has implemented specific support for the following fields:

- Name

  If not specified, a '/' will be used as name.

- Partner

  The value must be unique.
  Lookup logic : exact match on partner reference,
  if not found exact match on partner name.

- Product

  The value must be unique.
  A lookup will be peformed on the 'Internal Reference' (default_code) field of the Product record.
  In case of no result, a second lookup will be initiated on the Product Name.  
  
- Due date (or date_maturity)

  Date format must be yyyy-mm-dd)

- Currency

  Specify currency code, e.g. 'USD', 'EUR', ... )

- Analytic Account

  Lookup logic : exact match on code,
  if not found exact match on name.

- Tax Grids

  Comma separated list of the Tax Grids, e.g. +81D, +86

A blank column header indicates the end of the columns that will be
processed. This allows 'comment' columns on the input lines.

Empty lines or lines starting with '#' will be ignored.

Foreign currency support
------------------------

When the 'Currency' field is supplied without Amount Currency' than this field will be
computed. The compute is also performed when supplying 'Amount Currency' without 'Debit' or 'Credit'.


Input file example
------------------

Cf. directory 'static/sample_import_file' of this module.

