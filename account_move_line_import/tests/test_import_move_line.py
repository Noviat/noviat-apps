# Copyright 2009-2023 Noviat
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64

import odoo.tests
from odoo import fields
from odoo.modules.module import get_module_resource

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@odoo.tests.tagged("post_install", "-at_install")
class TestAccountMoveLineImport(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super(TestAccountMoveLineImport, cls).setUpClass()
        cls.aml_import_model = cls.env["aml.import"]
        cls.am_model = cls.env["account.move"]
        cls.module_name = __name__.split("addons.")[1].split(".")[0]

    def test_aml_file_import(self):

        am = self.am_model.create(
            {
                "date": fields.Date.today(),
                "journal_id": self.company_data["default_journal_misc"].id,
            }
        )
        aml_file_path = get_module_resource(
            self.module_name, "tests", "test_account_move_lines.csv"
        )
        aml_data = open(aml_file_path, "rb").read()
        aml_data = base64.encodebytes(aml_data)
        aml_import = self.aml_import_model.create(
            {
                "aml_data": aml_data,
                "csv_separator": ";",
                "decimal_separator": ",",
                "file_type": "csv",
                "codepage": "utf-8",
                "dialect": '{"delimiter": ";",'
                '"doublequote": true,'
                '"escapechar": null,'
                '"lineterminator": "\\n",'
                '"skipinitialspace": false}',
            }
        )
        aml_import.with_context(active_id=am.id).aml_import()
        self.assertEqual(am.amount_total, 5000.00)
