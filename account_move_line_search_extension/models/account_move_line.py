# Copyright 2009-2022 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import re

from lxml import etree

from odoo import api, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.model
    def _search(self, domain, *args, **kwargs):
        if "account_move_line_search_extension" in self.env.context:
            domain = self._get_amlse_domain(domain)
        return super()._search(domain, *args, **kwargs)

    @api.model
    def _web_read_group(self, domain, *args, **kwargs):
        if "account_move_line_search_extension" in self.env.context:
            domain = self._get_amlse_domain(domain)
        return super()._web_read_group(domain, *args, **kwargs)

    @api.model
    def fields_view_get(
        self, view_id=None, view_type="form", toolbar=False, submenu=False
    ):
        res = super().fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu
        )
        if view_type == "amlse":
            res["toolbar"] = super().fields_view_get(
                view_id=view_id, view_type="tree", toolbar=True, submenu=submenu
            )["toolbar"]
        if (
            self.env.context.get("account_move_line_search_extension")
            and view_type == "form"
        ):
            doc = etree.XML(res["arch"])
            form = doc.xpath("/form")
            for node in form:
                node.set("edit", "false")
                node.set("create", "false")
                node.set("delete", "false")
            res["arch"] = etree.tostring(doc)
        return res

    @api.model
    def get_amlse_render_dict(self):
        """
        The result of this method is merged into the
        action context for the Qweb rendering.
        """
        render_dict = {}
        for group in self._get_amlse_groups():
            if self.env.user.has_group(group):
                render_dict[group.replace(".", "_")] = True
        return render_dict

    def _get_amlse_groups(self):
        return ["analytic.group_analytic_accounting"]

    @api.model
    def _get_amlse_domain(self, domain):
        for dom in domain:
            if dom[0] == "amount_search" and len(dom) == 3:
                # digits = 2 for performance reasons:
                # retrieving the currency rounding would require
                # res_currency join and hence slower query
                digits = 2
                val = str2float(dom[2])
                if val is not None:
                    if dom[2][0] in ["+", "-"]:
                        f1 = "balance"
                        f2 = "amount_currency"
                    else:
                        f1 = "abs(balance)"
                        f2 = "abs(amount_currency)"
                        val = abs(val)
                    query = (
                        "SELECT id FROM account_move_line "
                        "WHERE round({0} - {2}, {3}) = 0.0 "
                        "OR round({1} - {2}, {3}) = 0.0"
                    ).format(f1, f2, val, digits)
                    # pylint: disable=E8103
                    self.env.cr.execute(query)
                    res = self.env.cr.fetchall()
                    ids = res and [x[0] for x in res] or [0]
                    dom[0] = "id"
                    dom[1] = "in"
                    dom[2] = ids
                else:
                    dom[0] = "id"
                    dom[1] = "="
                    dom[2] = 0
                break

        for dom in domain:
            if dom[0] == "analytic_account_search":
                ana_dom = [
                    "|",
                    ("name", "ilike", dom[2]),
                    ("code", "ilike", dom[2]),
                ]
                dom[0] = "analytic_account_id"
                dom[2] = self.env["account.analytic.account"].search(ana_dom).ids
        return domain


def str2float(val):
    pattern = re.compile("[0-9]")
    dot_comma = pattern.sub("", val)
    if dot_comma and dot_comma[-1] in [".", ","]:
        decimal_separator = dot_comma[-1]
    else:
        decimal_separator = False
    if decimal_separator == ".":
        val = val.replace(",", "")
    else:
        val = val.replace(".", "").replace(",", ".")
    try:
        return float(val)
    except Exception:
        return None
