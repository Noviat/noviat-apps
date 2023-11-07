# Copyright 2009-2023 Noviat.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).


def migrate(cr, version):
    cr.execute(
        """
    UPDATE account_bank_statement abs
      SET import_format = 'coda'
      FROM (
        SELECT DISTINCT(statement_id)
          FROM account_bank_statement_line
          WHERE coda_transaction_dict IS NOT NULL
      ) sq
      WHERE abs.id = sq.statement_id
        """
    )
