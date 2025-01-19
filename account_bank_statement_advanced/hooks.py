# Copyright 2024 Noviat
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).


def pre_init_hook(env):
    env.cr.execute(
        """
    SELECT column_name
      FROM information_schema.columns
      WHERE table_name='account_bank_statement_line'
        AND column_name='transaction_date'
        """
    )
    res = env.cr.fetchone()
    if not res:
        env.cr.execute(
            """
        ALTER TABLE account_bank_statement_line
          ADD COLUMN transaction_date date;
        UPDATE account_bank_statement_line absl
          SET transaction_date = am.date
        FROM account_move am
        WHERE absl.move_id = am.id;
            """
        )
