# Copyright 2009-2022 Noviat
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


def migrate(cr, version):

    cr.execute(
        """
    UPDATE account_tax at SET tax_group_id = imd2.res_id
      FROM ir_model_data imd1, ir_model_data imd2
      WHERE imd1.module='l10n_be_coa_multilang' AND imd2.module='l10n_be_coa_multilang'
        AND at.tax_group_id = imd1.res_id
        AND imd1.name LIKE 'atg_VAT_IN_%'
        AND imd2.name = REPLACE(imd1.name, '_IN_', '_OUT_');

    UPDATE account_tax at SET tax_group_id = imd2.res_id
      FROM ir_model_data imd1, ir_model_data imd2
      WHERE imd1.module='l10n_be_coa_multilang' AND imd2.module='account'
        AND at.tax_group_id = imd1.res_id
        AND imd1.name = 'atg_VAT_CASES'
        AND imd2.name = 'tax_group_taxes';

    UPDATE ir_model_data SET name = REPLACE(name, '_OUT', '');
        """
    )
