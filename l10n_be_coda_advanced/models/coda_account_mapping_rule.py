# Copyright 2009-2023 Noviat.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models
from odoo.tools.safe_eval import safe_eval

from ..wizards.coda_helpers import repl_special


class CodaAccountMappingRule(models.Model):
    _name = "coda.account.mapping.rule"
    _inherit = "analytic.mixin"
    _description = "Rules Engine to assign accounts during CODA parsing"
    _order = "sequence"

    coda_bank_account_id = fields.Many2one(
        comodel_name="coda.bank.account", string="CODA Bank Account", ondelete="cascade"
    )
    sequence = fields.Integer(
        help="Determines the order of the rules to assign accounts"
    )
    name = fields.Char(string="Rule Name", required=True)
    active = fields.Boolean(default=True, help="Switch on/off this rule.")
    company_id = fields.Many2one(related="coda_bank_account_id.company_id")
    # matching criteria
    partner_name = fields.Char(
        help="The name of the partner in the CODA Transaction."
        "\nYou can use this field to set a matching rule "
        "on Partners which are not (yet) registered in Odoo. "
    )
    counterparty_number = fields.Char(
        string="Account Number",
        help="The Bank Account Number of the Partner "
        "in the CODA Transaction."
        "\nYou can use this field to set a matching rule "
        "on Partners which are not (yet) registered in Odoo. ",
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Partner",
        ondelete="cascade",
        domain="['|', ('parent_id', '=', False), ('is_company' ,'=', True) ,"
        "'|', ('company_id', '=', company_id), ('company_id', '=', False)]",
        help="Use this field only if you have checked the 'Find Partner' " "option.",
    )
    trans_type_id = fields.Many2one(
        comodel_name="account.coda.trans.type", string="Transaction Type"
    )
    trans_family_id = fields.Many2one(
        comodel_name="account.coda.trans.code",
        string="Transaction Family",
        domain=[("type", "=", "family")],
    )
    trans_code_id = fields.Many2one(
        comodel_name="account.coda.trans.code",
        string="Transaction Code",
        domain="[('parent_id', '=', trans_family_id)]",
    )
    trans_category_id = fields.Many2one(
        comodel_name="account.coda.trans.category", string="Transaction Category"
    )
    freecomm = fields.Char(string="Free Communication", size=128)
    struct_comm_type_id = fields.Many2one(
        comodel_name="account.coda.comm.type", string="Structured Communication Type"
    )
    structcomm = fields.Char(string="Structured Communication", size=128)
    payment_reference = fields.Char(
        size=35,
        help="Payment Reference. For SEPA (SCT or SDD) transactions, "
        "the EndToEndReference is recorded in this field.",
    )
    # the split flag is required for the l10n_be_coda_card_cost module
    split = fields.Boolean(
        help="Split line into two separate lines with "
        "transaction amount and transaction cost."
    )
    # results
    account_id = fields.Many2one(
        comodel_name="account.account",
        string="Account",
        ondelete="cascade",
        domain="[('deprecated', '=', False), ('company_id', '=', parent.company_id)]",
    )
    account_tax_id = fields.Many2one(
        comodel_name="account.tax",
        string="Tax",
        ondelete="cascade",
        domain="[('company_id', '=', company_id)]",
        help="Select Tax object for bank costs. "
        "CODA files have seperate lines for Base and VAT amount, "
        "hence only simple tax objects containing the base (82) or "
        "deductible vat (59) case are supported, cf. VAT-V59 and "
        "VAT-V82 tax objects provided as part of the l10n_be_coa_multilang "
        "module. Expansion of a single transaction into multipe lines such "
        "as done by the 'Statement Operations' in the reconcile widget is "
        "not supported.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._strip_char_fields(vals)
        return super().create(vals_list)

    def write(self, vals):
        self._strip_char_fields(vals)
        return super().write(vals)

    def _strip_char_fields(self, vals):
        for fld in self._get_strip_char_fields():
            if vals.get(fld):
                vals[fld] = vals[fld].strip()

    @api.model
    def _rule_get(self, transaction, st_line, coda_bank_account):

        if transaction["struct_comm_type"]:
            structcomm = transaction["communication"]
            freecomm = None
        else:
            structcomm = None
            freecomm = transaction["communication"]
            if not freecomm and transaction.get("upper_transaction"):
                freecomm = repl_special(
                    transaction["upper_transaction"]["communication"].strip()
                )

        eval_dict = {
            "coda_bank_account_id": coda_bank_account.id,
            "partner_name": transaction["partner_name"] or None,
            "counterparty_number": transaction["counterparty_number"] or None,
            "partner_id": transaction["matching_info"].get("partner_id"),
            "trans_type_id": transaction["trans_type_id"],
            "trans_family_id": transaction["trans_family_id"],
            "trans_code_id": transaction["trans_code_id"],
            "trans_category_id": transaction["trans_category_id"],
            "struct_comm_type_id": transaction["struct_comm_type_id"],
            "freecomm": freecomm,
            "structcomm": structcomm,
            "payment_reference": transaction["payment_reference"] or None,
        }

        select = (
            "SELECT partner_name, counterparty_number, partner_id, "
            "trans_type_id, trans_family_id, trans_code_id, "
            "trans_category_id, "
            "struct_comm_type_id, freecomm, structcomm, "
            "account_id, analytic_distribution, account_tax_id, payment_reference"
        )
        select += self._rule_select_extra(coda_bank_account) + " "
        select += (
            "FROM coda_account_mapping_rule "
            "WHERE active = True AND coda_bank_account_id = {cba_id} "
            "ORDER BY sequence"
        ).format(cba_id=coda_bank_account.id)
        self.env.cr.execute(select)
        rules = self.env.cr.dictfetchall()
        condition = (
            "(not rule['partner_name'] or "
            "(partner_name == rule['partner_name'])) and "
            "(not rule['counterparty_number'] or "
            "(counterparty_number == rule['counterparty_number'])) and "
            "(not rule['trans_type_id'] or "
            "(trans_type_id == rule['trans_type_id'])) and "
            "(not rule['trans_family_id'] or "
            "(trans_family_id == rule['trans_family_id'])) "
            "and (not rule['trans_code_id'] or "
            "(trans_code_id == rule['trans_code_id'])) and "
            "(not rule['trans_category_id'] or "
            "(trans_category_id == rule['trans_category_id'])) "
            "and (not rule['struct_comm_type_id'] or "
            "(struct_comm_type_id == rule['struct_comm_type_id'])) and "
            "(not rule['partner_id'] or "
            "(partner_id == rule['partner_id'])) "
            "and (not rule['freecomm'] or (rule['freecomm'].lower() in "
            "(freecomm and freecomm.lower() or ''))) "
            "and (not rule['structcomm'] or "
            "(rule['structcomm'] in (structcomm or ''))) "
            "and (not rule['payment_reference'] or "
            "(rule['payment_reference'] in (payment_reference or ''))) "
        )
        result_fields = [
            "account_id",
            "account_tax_id",
            "analytic_distribution",
        ]
        result_fields += self._rule_result_extra(coda_bank_account.id)
        res = {}
        for rule in rules:
            if safe_eval(condition, dict(eval_dict, rule=rule)):
                for f in result_fields:
                    res[f] = rule[f]
                break
        return res

    def _rule_select_extra(self, coda_bank_account):
        """
        Use this method to customize the mapping rule engine.
        """
        return ""

    def _rule_result_extra(self, coda_bank_account):
        """
        Use this method to customize the mapping rule engine.
        """
        return []

    def _get_strip_char_fields(self):
        return ["partner_name", "counterparty_number"]
