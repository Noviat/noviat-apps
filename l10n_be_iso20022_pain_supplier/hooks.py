# Copyright 2009-2024 Noviat
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


def pre_init_hook(env):
    """
    Installations which had l10n_be_iso20022_pain installed may have
    account.payment.line entries with communication_type set to 'bba'.
    In this module we use the uppercase variant in order to be conform
    with the febelfin recommendations (https://www.febelfin.be).
    """
    env.cr.execute(
        """
        SELECT id FROM ir_model_fields
        WHERE model = 'account.payment.line'
          AND name = 'communication_type'
        """
    )
    field_id = env.cr.fetchone()[0]
    env.cr.execute(
        """
        DELETE FROM ir_model_fields_selection
        WHERE field_id = %s AND value = 'bba'
        """,
        (field_id,),
    )
    env.cr.execute(
        """
        UPDATE account_payment_line
        SET communication_type = 'BBA'
        WHERE communication_type = 'bba'
        """
    )
