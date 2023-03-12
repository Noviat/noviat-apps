# Copyright 2009-2023 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from lxml import etree

from odoo import api, models


class AccountPaymentLine(models.Model):
    _inherit = "account.payment.line"

    @api.model
    def fields_view_get(
        self, view_id=None, view_type="form", toolbar=False, submenu=False
    ):
        res = super().fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu
        )
        if self._context.get("payment_line_readonly") and view_type in ["tree", "form"]:
            doc = etree.XML(res["arch"])
            tree = doc.xpath("/tree")
            for node in tree:
                if "editable" in node.attrib:
                    del node.attrib["editable"]
            form = doc.xpath("/form")
            for el in [tree, form]:
                for node in el:
                    node.set("edit", "false")
                    node.set("create", "false")
                    node.set("delete", "false")
            res["arch"] = etree.tostring(doc)
        return res

    @api.model
    def _search(
        self,
        args,
        offset=0,
        limit=None,
        order=None,
        count=False,
        access_rights_uid=None,
    ):
        """
        Temporary fix while waiting on merge of
        https://github.com/OCA/bank-payment/pull/656
        """
        if self.env.context.get("account_payment_order_fixes"):
            company_id = self.env.context["company_id"]
            # Exclude lines that are already in a non-cancelled payment order
            self.env.cr.execute(
                """
            SELECT apl.id FROM account_payment_line apl
            INNER JOIN account_payment_order apo
              ON apl.order_id = apo.id
            INNER JOIN account_move_line aml
              ON aml.id = apl.move_line_id
            WHERE apo.state != 'cancel'
              AND aml.company_id = %s
              AND COALESCE(aml.reconciled, FALSE) = FALSE
                """,
                (company_id,),
            )
            res = self.env.cr.fetchall()
            return [x[0] for x in res]
        return super()._search(
            args,
            offset=offset,
            limit=limit,
            order=order,
            count=count,
            access_rights_uid=access_rights_uid,
        )
