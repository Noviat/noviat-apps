# Copyright 2009-2021 Noviat
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


def migrate(cr, version):
    cr.execute(
        """
    SELECT column_name
      FROM information_schema.columns
      WHERE table_name='be_scheme_account_tag_rel'
        AND column_name='be_legal_financial_reportscheme_id'
        """
    )
    res = cr.fetchone()
    if res:
        # drop table, ORM will recreate with correct data
        cr.execute("DROP TABLE be_scheme_account_tag_rel")
