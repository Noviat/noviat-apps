# Copyright 2009-2021 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from itertools import combinations

from odoo import models


class AccountCodaImport(models.TransientModel):
    _inherit = "account.coda.import"

    def _get_sale_order(self, st_line, cba, transaction, reconcile_note):
        """
        check matching Sales Order number in free form communication
        """
        free_comm = repl_special(transaction["communication"].strip())
        # pylint: disable=E8103
        select = (
            "SELECT id FROM (SELECT id, name, '%s'::text AS free_comm, "
            "regexp_replace(name, '[0]{3,10}', '0%%0') AS name_match "
            "FROM sale_order WHERE state not in ('cancel', 'done') "
            "AND company_id = %s) sq "
            "WHERE free_comm ILIKE '%%'||name_match||'%%'"
        ) % (free_comm, cba.company_id.id)
        self.env.cr.execute(select)
        res = self.env.cr.fetchall()
        return reconcile_note, res

    def _match_sale_order(self, st_line, cba, transaction, reconcile_note):
        match = transaction["matching_info"]

        if match["status"] in ["break", "done"]:
            return reconcile_note

        if (
            transaction["communication"]
            and cba.find_so_number
            and transaction["amount"] > 0
        ):
            reconcile_note, so_res = self._get_sale_order(
                st_line, cba, transaction, reconcile_note
            )
            if so_res and len(so_res) == 1:
                so_id = so_res[0][0]
                match["status"] = "done"
                match["sale_order_id"] = so_id
                sale_order = self.env["sale.order"].browse(so_id)
                partner = sale_order.partner_id.commercial_partner_id
                match["partner_id"] = partner.id
                reconcile_note = self._so_invoice_amount_match(
                    sale_order.invoice_ids, cba, transaction, reconcile_note
                )

        return reconcile_note

    def _so_invoice_amount_match(self, invoices, cba, transaction, reconcile_note):
        if not invoices:
            return reconcile_note

        if invoices.mapped("currency_id") != cba.currency_id:
            return reconcile_note

        cur = cba.currency_id
        amls = invoices.mapped("line_ids").filtered(
            lambda r: r.account_id.internal_type == "receivable" and not r.reconciled
        )
        if cur == cba.company_id.currency_id:
            amt_fld = "amount_residual"
        else:
            amt_fld = "amount_residual_currency"
        matching_amls = []
        for i in range(len(amls)):
            to_check = combinations(amls, i + 1)
            for entry in to_check:
                amount = 0.0
                for aml in entry:
                    amount += getattr(aml, amt_fld)
                if cur.is_zero(transaction["amount"] - amount):
                    matching_amls.append(entry)

        matching_amls = matching_amls and matching_amls[0]
        if matching_amls:
            transaction["matching_info"]["counterpart_amls"] = [
                (aml, getattr(aml, amt_fld)) for aml in matching_amls
            ]
        return reconcile_note


def repl_special(s):
    s = s.replace("'", "'" + "'")
    return s
