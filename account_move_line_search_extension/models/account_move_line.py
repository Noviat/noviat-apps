# Copyright 2009-2023 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import re
from datetime import date

from dateutil.relativedelta import relativedelta

from odoo import api, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.model
    def _search(self, domain, *args, **kwargs):
        if "account_move_line_search_extension" in self.env.context:
            self._update_amlse_domain(domain)
        return super()._search(domain, *args, **kwargs)

    @api.model
    def _web_read_group(self, domain, *args, **kwargs):
        if "account_move_line_search_extension" in self.env.context:
            self._update_amlse_domain(domain)
        return super()._web_read_group(domain, *args, **kwargs)

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
    def _update_amlse_domain(self, domain):
        self._handle_amount_search(domain)
        self._handle_period_search(domain)
        # self._handle_analytic_search(domain)

    def _handle_amount_search(self, domain):
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

    def _handle_period_search(self, domain):
        period_search = False
        for _i, dom in enumerate(domain):
            if dom[0] == "period_search" and len(dom) == 3:
                period_search = True
                period = dom[2].strip()
                dates = self._compute_period_search_dates(period)
                if dates:
                    date_start, date_stop = dates
                break
        if period_search:
            if dates:
                domain[_i] = ("date", ">=", date_start)
                domain.insert(_i + 1, ("date", "<=", date_stop))
            else:
                domain[_i] = ("id", "=", 0)

    def _compute_period_search_dates(self, period):
        groups = [period]
        for separator in [" ", "/", "-"]:
            if separator in period:
                groups = period.split(separator)
                break
        groups = [x.strip() for x in groups]
        groups = [x for x in groups if len(x) in (2, 4)]
        years = []
        mqs = []
        for group in groups:
            if len(group) == 4 and group.isdigit():
                years.append(group)
            elif len(group) == 2 and not mqs:
                mqs.append(group)
        if len(years) > 1 or len(mqs) > 1:
            return

        year = years and years[0]
        mqs = mqs and mqs[0]
        if not (year or mqs):
            return

        year = year and int(year) or date.today().year
        month_start = 1
        month_stop = 12
        if mqs:
            if mqs.isdigit():
                month = int(mqs)
                if 1 <= month <= 12:
                    month_start = month_stop = month
            elif mqs[0].upper() == "Q" and mqs[1].isdigit():
                quarter = int(mqs[1])
                if quarter in (1, 2, 3, 4):
                    month_start = 1 + (quarter - 1) * 3
                    month_stop = month_start + 2
            elif mqs[0].upper() == "H" and mqs[1].isdigit():
                semester = int(mqs[1])
                if semester == 1:
                    month_stop = 6
                elif semester == 2:
                    month_start = 7
            else:
                return

        date_start = date(year, month_start, 1)
        date_stop = date(year, month_stop, 1) + relativedelta(months=1, days=-1)
        return date_start, date_stop

    # def _handle_analytic_search(self, domain):
    #     for dom in domain:
    #         if dom[0] == "analytic_account_search":
    #             ana_dom = [
    #                 "|",
    #                 ("name", "ilike", dom[2]),
    #                 ("code", "ilike", dom[2]),
    #             ]
    #             dom[0] = "analytic_account_id"
    #             dom[2] = self.env["account.analytic.account"].search(ana_dom).ids


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
