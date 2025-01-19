# Copyright 2009-2024 Noviat
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, models

from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @template("be_coa")
    def _get_be_coa_template_data(self):
        return {
            "name": _("Accounting with legal reports"),
            "visible": True,
            "code_digits": "6",
            "property_account_receivable_id": "aatn_400000",
            "property_account_payable_id": "aatn_440000",
            "property_account_expense_categ_id": "aatn_600000",
            "property_account_income_categ_id": "aatn_700000",
        }

    @template("be_coa", "res.company")
    def _get_be_coa_res_company(self):
        return {
            self.env.company.id: {
                "account_fiscal_country_id": "base.be",
                "bank_account_code_prefix": "550",
                "cash_account_code_prefix": "570",
                "transfer_account_code_prefix": "580",
                "account_default_pos_receivable_account_id": "aatn_400100",
                "income_currency_exchange_account_id": "aatn_754000",
                "expense_currency_exchange_account_id": "aatn_654000",
                "account_journal_suspense_account_id": "aatn_599000",
                "account_journal_early_pay_discount_loss_account_id": "aatn_657000",
                "account_journal_early_pay_discount_gain_account_id": "aatn_758400",
                "account_sale_tax_id": "attn_VAT-OUT-21-G",
                "account_purchase_tax_id": "attn_VAT-IN-V81-21-G",
                "default_cash_difference_income_account_id": "aatn_758400",
                "default_cash_difference_expense_account_id": "aatn_658400",
                "transfer_account_id": "aatn_580000",
            },
        }

    @template("be_coa", "account.journal")
    def _get_be_coa_account_journal(self):
        return {
            "sale": {"refund_sequence": True},
            "purchase": {"refund_sequence": True},
        }

    @template("be_coa", "account.reconcile.model")
    def _get_be_coa_reconcile_model(self):
        return {  # TODO
            #            'escompte_template': {
            #                'name': 'Cash Discount',
            #                'line_ids': [
            #                    Command.create({
            #                        'account_id': 'a653',
            #                        'amount_type': 'percentage',
            #                        'amount_string': '100',
            #                        'label': 'Cash Discount Granted',
            #                    }),
            #                ],
            #                'name@fr': 'Escompte',
            #                'name@nl': 'Betalingskorting',
            #                'name@de': 'Skonto',
            #            },
            #            'frais_bancaires_htva_template': {
            #                'name': 'Bank Fees (No VAT)',
            #                'line_ids': [
            #                    Command.create({
            #                        'account_id': 'a6560',
            #                        'amount_type': 'percentage',
            #                        'amount_string': '100',
            #                        'label': 'Bank Fees (No VAT)',
            #                    }),
            #                ],
            #                'name@fr': 'Frais bancaires (Hors TVA)',
            #                'name@nl': 'Bankkosten (Geen BTW)',
            #                'name@de': 'Bankgebühren (Ohne MwSt.)',
            #            },
            #            'frais_bancaires_tva21_template': {
            #                'name': 'Bank Fees (21% VAT)',
            #                'line_ids': [
            #                    Command.create({
            #                        'account_id': 'a6560',
            #                        'amount_type': 'percentage',
            #                        'tax_ids': [
            #                            Command.set([
            #                                'attn_TVA-21-inclus-dans-prix',
            #                            ]),
            #                        ],
            #                        'amount_string': '100',
            #                        'label': 'Bank Fees (21% VAT)',
            #                    }),
            #                ],
            #                'name@fr': 'Frais bancaires (21% TVA)',
            #                'name@nl': 'Bankkosten (21% BTW)',
            #                'name@de': 'Bankgebühren (21 % MwSt.)',
            #            },
            #            'virements_internes_template': {
            #                'name': 'Internal Transfers',
            #                'to_check': False,
            #                'line_ids': [
            #                    Command.create({
            #                        'account_id': 'a58',
            #                        'amount_type': 'percentage',
            #                        'amount_string': '100',
            #                        'label': 'Internal Transfers',
            #                    }),
            #                ],
            #                'name@fr': 'Virements internes',
            #                'name@nl': 'Interne overboekingen',
            #                'name@de': 'Interne Überweisungen',
            #            },
        }
