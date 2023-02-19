.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

===================
Import Fixed Assets
===================

This module allows the import of Fixed Assets from an excel file.

Before starting the import a number of sanity checks are performed such as:

- check for duplicates
- check if asset profiles are correct

If no issues are found the assets will be loaded.
The resulting Fixed Assets will be in draft mode to allow a final check before confirming the asset.

Usage
=====

Input file column headers
-------------------------

Mandatory Fields
''''''''''''''''

- Reference

  The Reference is checked for uniqueness to avoid loading of duplicate assets.


- Asset Name

- Asset Profile

- Purchase Value

  Purchase Value in Company Currency

- Asset Start Date

  Date format must be yyyy-mm-dd

Other Fields
''''''''''''

Extra columns can be added and will be processed as long as
the column header is equal to the 'ORM' name of the field.
Input fields with no corresponding ORM field will be ignored
unless special support has been added for that field in this
module (or a module that extends the capabilities of this module).

This module has implemented specific support for the following fields:

- Partner

  The value must be unique.
  Lookup logic : exact match on partner reference,
  if not found exact match on partner name.


A blank column header indicates the end of the columns that will be
processed. This allows 'comment' columns on the input lines.

Empty lines or lines starting with '#' will be ignored.
