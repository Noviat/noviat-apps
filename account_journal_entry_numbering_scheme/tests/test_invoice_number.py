# Copyright 2009-2023 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


class TestInvoiceNumber(AccountTestInvoicingCommon):
    def setUp(self):
        super().setUp()
        self.sale_journal = self.company_data["default_journal_sale"]
        self.c1 = self.env["res.partner"].create({"name": "c1"})

    def test_journal_override_sequence_regex(self):
        self.sale_journal.starting_sequence = "VF2101000"
        self.sale_journal.sequence_override_regex = (
            r"(?P<prefix1>[A-Z]{1,})(?P<year>\d{2})(?P<month>\d{2})(?P<seq>\d{3,})"
        )
        inv1 = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "invoice_date": "2021-01-01",
                "partner_id": self.c1.id,
                "journal_id": self.company_data["default_journal_sale"].id,
                "line_ids": [
                    (
                        0,
                        None,
                        {
                            "name": "revenue line 1",
                            "account_id": self.company_data[
                                "default_account_revenue"
                            ].id,
                            "debit": 0.0,
                            "credit": 100.0,
                        },
                    ),
                    (
                        0,
                        None,
                        {
                            "name": "counterpart line",
                            "account_id": self.company_data[
                                "default_account_receivable"
                            ].id,
                            "debit": 100.0,
                            "credit": 0.0,
                        },
                    ),
                ],
            }
        )
        inv1.action_post()
        self.assertEqual(inv1.name, "VF2101001")

        inv2 = inv1.copy({"invoice_date": "2021-08-05"})
        inv2.action_post()
        self.assertEqual(inv2.name, "VF2108001")
