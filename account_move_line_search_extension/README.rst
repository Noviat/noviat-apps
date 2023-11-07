.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

==============================
Journal Items Search Extension
==============================

This module adds the 'Journal Items Search All' menu entry.

This menu entry adds a number of search fields on top of the List View rows.
These fields can be used in combination with the Search window.

The purpose of this view is to offer a fast drill down capability
when searching through large number of accounting entries.

The drill down is facilitated further by opening the Form View when clicking on
the sought-after entry.
This allows an intuitive click-through to the related accounting documents
such as the originating Bank Statement, Invoice, Asset, ...

|

Search fields
=============

Extra search logic has been added behind the following fields:

- amount: the amount field is looked up in both the debit and credit fields

- period: the data entered is parsed to identify a 4 digit and a 2 characters group

  The 4 digits gourp will be used to search on year.
  
  The 2 character group (if present) will refine the search with month, quarter or semester.   
   
  If only a 2 character group is entered than the year will be considered the current year.
  
  Year and Month/Quarter/Semester groups can be seperated by spaces, / or - characters.

  Examples:

  01/2019: January 2019
  
  2020-Q2: Second Quarter of 2020
  
  H1 2002: First Semester of 2002

  
Known Issues / Roadmap
======================

Add support for

- analytic accounts


