.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

=========================
account journal lock date
=========================

This module is inspired by the OCA account_journal_lock_date 11.0 module.
Differences compared to the OCA 13.O account_journal_lock_date module:

- Single Lock Date field. By default a Lock Date on a journal will lock operations for all users,
  including the Financial Advisor (can be relaxed via an inherited module).
- The Lock Date will be checked when posting the Journal Entries, hence not while creating draft invoices.
