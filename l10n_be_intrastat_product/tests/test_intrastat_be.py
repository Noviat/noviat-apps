# Copyright 2009-2022 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests import Form, SavepointCase


class TestIntrastatBe(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.inv_obj = cls.env["account.move"]
        cls.fpos_obj = cls.env["account.fiscal.position"]
        cls.region_obj = cls.env["intrastat.region"]
        cls.decl_obj = cls.env["l10n.be.intrastat.product.declaration"]

        cls.company = cls.env.company
        cls.env.company.country_id = cls.env.ref("base.be")
        cls.journal_sale = cls.env["account.journal"].create(
            {
                "name": "Test Sales Journal",
                "code": "tSAL",
                "type": "sale",
                "company_id": cls.company.id,
            }
        )
        cls.journal_purchase = cls.env["account.journal"].create(
            {
                "name": "Test Purchases Journal",
                "code": "tPUR",
                "type": "purchase",
                "company_id": cls.company.id,
            }
        )
        cls.acc_ar = cls.env["account.account"].create(
            {
                "name": "AR",
                "code": "T-400000",
                "reconcile": True,
                "user_type_id": cls.env.ref("account.data_account_type_receivable").id,
                "company_id": cls.company.id,
            }
        )
        cls.acc_ap = cls.env["account.account"].create(
            {
                "name": "AP",
                "code": "T-440000",
                "reconcile": True,
                "user_type_id": cls.env.ref("account.data_account_type_payable").id,
                "company_id": cls.company.id,
            }
        )
        cls.acc_inc = cls.env["account.account"].create(
            {
                "name": "Income",
                "code": "T-700000",
                "user_type_id": cls.env.ref("account.data_account_type_revenue").id,
                "company_id": cls.company.id,
            }
        )
        cls.acc_exp = cls.env["account.account"].create(
            {
                "name": "Expense",
                "code": "T-600000",
                "user_type_id": cls.env.ref("account.data_account_type_expenses").id,
                "company_id": cls.company.id,
            }
        )
        cls.company.intrastat_region_id = cls.env.ref(
            "l10n_be_intrastat_product.intrastat_region_2"
        )
        cls.hs_code_cn = cls.env["hs.code"].create(
            {
                "description": "Rough discount, credit notes",
                "local_code": "99600000",
                "intrastat_unit_id": cls.env.ref(
                    "intrastat_product.intrastat_unit_pce"
                ).id,
            }
        )
        cls.hs_code_horse = cls.env["hs.code"].create(
            {
                "description": "Horse",
                "local_code": "01012100",
                "intrastat_unit_id": cls.env.ref(
                    "intrastat_product.intrastat_unit_pce"
                ).id,
            }
        )
        cls.product_horse = cls.env["product.product"].create(
            {
                "name": "Horse",
                "weight": 500.0,
                "list_price": 5000.0,
                "standard_price": 3000.0,
                "origin_country_id": cls.env.ref("base.be").id,
                "hs_code_id": cls.hs_code_horse.id,
                "property_account_income_id": cls.acc_inc.id,
                "property_account_expense_id": cls.acc_exp.id,
            }
        )
        cls.product_foal = cls.env["product.product"].create(
            {
                "name": "Foal",
                "weight": 230.0,
                "list_price": 2000.0,
                "standard_price": 1200.0,
                "origin_country_id": cls.env.ref("base.be").id,
                "hs_code_id": cls.hs_code_horse.id,
                "property_account_income_id": cls.acc_inc.id,
                "property_account_expense_id": cls.acc_exp.id,
            }
        )
        cls.partner_b2b_1 = cls.env["res.partner"].create(
            {
                "name": "NL B2B 1",
                "country_id": cls.env.ref("base.nl").id,
                "is_company": True,
                "vat": "NL 123456782B90",
                "property_account_receivable_id": cls.acc_ar.id,
                "property_account_payable_id": cls.acc_ap.id,
            }
        )
        cls.partner_b2b_2 = cls.env["res.partner"].create(
            {
                "name": "NL B2B 2",
                "country_id": cls.env.ref("base.nl").id,
                "is_company": True,
                "vat": "NL000000000B00",
                "property_account_receivable_id": cls.acc_ar.id,
                "property_account_payable_id": cls.acc_ap.id,
            }
        )

    def test_be_sale_b2b(self):

        inv_out = self.inv_obj.with_context(default_type="out_invoice").create(
            {"partner_id": self.partner_b2b_1.id, "journal_id": self.journal_sale.id}
        )
        with Form(inv_out) as inv_form:
            with inv_form.invoice_line_ids.new() as ail:
                ail.product_id = self.product_horse
        inv_out.action_post()

        declaration = self.decl_obj.create(
            {
                "type": "dispatches",
                "company_id": self.env.company.id,
                "year": str(inv_out.date.year),
                "month": str(inv_out.date.month).zfill(2),
            }
        )
        declaration.action_gather()
        declaration.generate_declaration()
        clines = declaration.computation_line_ids
        dlines = declaration.declaration_line_ids
        self.assertEqual(clines[0].vat_number, "NL123456782B90")
        self.assertEqual(dlines[0].src_dest_country_code, "NL")

    def test_be_purchase(self):

        inv_in1 = self.inv_obj.with_context(default_type="in_invoice").create(
            {
                "partner_id": self.partner_b2b_1.id,
                "journal_id": self.journal_purchase.id,
            }
        )
        with Form(inv_in1) as inv_form:
            with inv_form.invoice_line_ids.new() as ail:
                ail.product_id = self.product_horse
        inv_in1.invoice_date = inv_in1.date
        inv_in1.action_post()

        inv_in2 = self.inv_obj.with_context(default_type="in_invoice").create(
            {"partner_id": self.partner_b2b_2.id}
        )
        with Form(inv_in2) as inv_form:
            with inv_form.invoice_line_ids.new() as ail:
                ail.product_id = self.product_foal
                ail.quantity = 2.0
        inv_in2.invoice_date = inv_in2.date
        inv_in2.action_post()

        declaration = self.decl_obj.create(
            {
                "type": "arrivals",
                "company_id": self.env.company.id,
                "year": str(inv_in1.date.year),
                "month": str(inv_in1.date.month).zfill(2),
            }
        )
        declaration.action_gather()
        declaration.generate_declaration()
        clines = declaration.computation_line_ids
        dlines = declaration.declaration_line_ids
        cline_foal = clines.filtered(lambda r: r.product_id == self.product_foal)
        self.assertEqual(cline_foal.weight, 460.0)
        self.assertEqual(dlines.amount_company_currency, 5400.0)
