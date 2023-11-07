# Copyright 2009-2023 Noviat.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import odoo.tests

# from odoo.addons.account_inter_company_rules.tests.common import TestInterCompanyRulesCommon
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@odoo.tests.tagged("post_install", "-at_install")
class TestInterCompanyInvoiceExtensions(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company_a = cls.company_data["company"]
        cls.company_a.rule_type = "invoice_and_refund"
        cls.company_b = cls.company_data_2["company"]
        cls.company_b.rule_type = "invoice_and_refund"
        # Create customer invoices for company A
        # cls.res_users_company_a.company_ids = [(4, cls.company_b.id)]
        # Create user of company_a
        cls.res_users_company_a = cls.env["res.users"].create(
            {
                "name": "User A",
                "login": "usera",
                "email": "usera@yourcompany.com",
                "company_id": cls.company_a.id,
                "company_ids": [(6, 0, [cls.company_a.id])],
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            cls.env.ref("account.group_account_user").id,
                            cls.env.ref("account.group_account_manager").id,
                        ],
                    )
                ],
            }
        )
        cls.customer_invoice = (
            cls.env["account.move"]
            .with_user(cls.res_users_company_a)
            .create(
                {
                    "move_type": "out_invoice",
                    "partner_id": cls.company_b.partner_id.id,
                    "currency_id": cls.env.ref("base.EUR").id,
                    "invoice_line_ids": [
                        (
                            0,
                            0,
                            {
                                "product_id": cls.product_a.id,
                                "price_unit": 1000.0,
                                "quantity": 1.0,
                                "name": "product_a",
                            },
                        )
                    ],
                }
            )
        )
        cls.journal_sale = cls.company_data["default_journal_sale"]
        cls.journal_sale_refund = cls.journal_sale.copy(
            default={"alias_name": "Refund Vendor"}
        )
        cls.journal_sale_refund.write(
            {
                "name": "Customer Refunds",
                "code": "S-REF",
            }
        )
        cls.journal_sale_interco = cls.journal_sale.copy(
            default={"alias_name": "Interco Vendor"}
        )
        cls.journal_sale_interco.write(
            {
                "name": "Customer Invoices Intercompany",
                "code": "S-ICO",
            }
        )

        # "alias_name": "Interco Vendor",

        cls.customer_invoice_interco = cls.customer_invoice.copy(
            default={"journal_id": cls.journal_sale_interco.id}
        )
        cls.customer_refund = cls.customer_invoice._reverse_moves(
            default_values_list=[{"journal_id": cls.journal_sale_refund.id}]
        )

        # Validate invoice
        cls.customer_invoice.with_user(cls.res_users_company_a).action_post()
        cls.customer_invoice_interco.with_user(cls.res_users_company_a).action_post()
        cls.customer_refund.with_user(cls.res_users_company_a).action_post()

        # Create 3 journals in company b
        cls.journal_purchase = cls.company_data_2["default_journal_purchase"]

        cls.journal_purchase_interco = cls.journal_purchase.copy(
            default={"alias_name": "Supplier Interco alias"}
        )
        cls.journal_purchase_interco.write(
            {
                "name": "Incoming Invoice Journal Intercompany",
                "code": "P-ICO",
            }
        )

        cls.journal_purchase_refund = cls.journal_purchase.copy(
            default={"alias_name": "Supplier Refunds alias"}
        )
        cls.journal_purchase_refund.write(
            {
                "name": "Supplier Refunds",
                "code": "P-REF",
            }
        )

        # Create the mapping

        cls.mapping = cls.env["account.reinvoice.journal.mapping.multi.company"].create(
            [
                {
                    "sequence": 10,
                    "journal_out_ids": [
                        (4, cls.journal_sale.id),
                        (4, cls.journal_sale_refund.id),
                        (4, cls.journal_sale_interco.id),
                    ],
                    "target_company": str(cls.company_b.id),
                    "target_journal_id": cls.journal_purchase.id,
                    "target_refund_journal_id": cls.journal_purchase_refund.id,
                    "company_id": cls.company_a.id,
                },
                {
                    "sequence": 20,
                    "journal_out_ids": [(4, cls.journal_sale_interco.id)],
                    "target_company": str(cls.company_b.id),
                    "target_journal_id": cls.journal_purchase_interco.id,
                    "target_refund_journal_id": cls.journal_purchase_refund.id,
                    "company_id": cls.company_a.id,
                },
            ]
        )

        def test_button_draft(self):

            try:
                # Call the button_draft method
                self.customer_invoice.with_user(self.res_users_company_a).button_draft()

                # If the button_draft method didn't raise an exception, the test should fail
                self.fail(
                    "Expected UserError exception for button Draft was not raised"
                )

            except odoo.exceptions.UserError as e:
                expected_error_message = (
                    "You can only reset to draft an Intercompany Invoice "
                    "if the associated Supplier Invoice in the "
                    "target company has been set to state 'Cancel'."
                )
                self.assertEqual(
                    e.name,
                    expected_error_message,
                    "Error message doesn't match expected value",
                )

        def test_button_cancel(self):

            try:
                # Call the button_cancel method
                self.customer_invoice.with_user(
                    self.res_users_company_a
                ).button_cancel()

                # If the button_cancel method didn't raise an exception, the test should fail
                self.fail(
                    "Expected UserError exception for button Cancel was not raised"
                )

            except odoo.exceptions.UserError as e:
                expected_error_message = (
                    "You can only reset to draft an Intercompany Invoice "
                    "if the associated Supplier Invoice in the "
                    "target company has been set to state 'Cancel'."
                )
                self.assertEqual(
                    e.name,
                    expected_error_message,
                    "Error message doesn't match expected value",
                )

    def test_inter_company_prepare_invoice_data(self):
        """
        We will test one normal invoice, one intercompany invoice and one normal refund
        """
        supplier_invoice = self.customer_invoice.intercompany_invoice_id
        supplier_invoice_interco = self.customer_invoice_interco.intercompany_invoice_id
        supplier_invoice_refund = self.customer_refund._inter_company_create_invoices()

        self.assertEqual(
            supplier_invoice.journal_id.id,
            self.journal_purchase.id,
            "Journal mismatch for normal invoice",
        )
        self.assertEqual(
            supplier_invoice_refund.journal_id.id,
            self.journal_purchase_refund.id,
            "Journal mismatch for normal refund",
        )

        self.assertEqual(
            supplier_invoice_interco.journal_id.id,
            self.journal_purchase_interco.id,
            "Journal mismatch for intercompany invoice",
        )
