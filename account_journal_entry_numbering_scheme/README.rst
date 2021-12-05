.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

=================================
Customise Journal Entry Numbering
=================================

This module allows to set the regex expression used to generate the Journal Entry numbering scheme.


Configuration
=============

Set the following fields via the Journal Advanced Settings:

- Starting Sequence
- Refund Starting Sequence
- Sequence Override Regex

This is a regex that can include all the following capture groups: prefix1, year, prefix2, month, prefix3, seq, suffix.

The prefix* groups are the separators between the year, month and the actual increasing sequence number (seq).

|

e.g:

- Starting Sequence : INV2101000
- Refund Starting Sequence : RINV2101000
- Sequence Override Regex : (?P<prefix1>[A-Z]{1,})(?P<year>\d{2})(?P<month>\d{2})(?P<seq>\d{3,})

This expressions defines the following invoice numbering scheme : INVYYMMSSS whereby SSS will restart at 001 on a monthly basis.

This will result in the following invoice number for e.g. the third invoice of Februari 2021 : INV2102003

|

The following regex will be used if you do not set the Sequence Override Regex:

^(?P<prefix1>.*?)(?P<year>((?<=\D)|(?<=^))(\d{4}|(\d{2}(?=\D))))(?P<prefix2>\D*?)(?P<month>\d{2})(?P<prefix3>\D+?)(?P<seq>\d*)(?P<suffix>\D*?)$


Credits
=======

Contributors
------------

* Luc De Meyer <luc.demeyer@noviat.com>
