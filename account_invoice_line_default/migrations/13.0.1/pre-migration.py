# Copyright 2009-2021 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


def migrate(cr, version):
    if not version:
        return

    cr.execute(
        """
        SELECT id, name FROM ir_model_fields
          WHERE name like 'property_in_inv_acc%'
          AND model='res.partner';
        """
    )
    res = cr.fetchall()
    field_id, field_name = res[0]
    if field_name == "property_in_inv_account_id":
        fn_in_old = "property_in_inv_account_id"
        fn_out_old = "property_out_inv_account_id"
    else:
        fn_in_old = "property_in_inv_acc"
        fn_out_old = "property_out_inv_acc"
    cr.execute(  # pylint: disable=E8103
        """
        UPDATE ir_property
          SET name='property_in_inv_account_id', fields_id=%s
          WHERE name='%s';
        UPDATE ir_property
          SET name='property_out_inv_account_id', fields_id=%s
          WHERE name='%s';
        """
        % (field_id, fn_in_old, field_id, fn_out_old)
    )
