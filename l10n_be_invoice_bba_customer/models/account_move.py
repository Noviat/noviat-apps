# Copyright 2009-2024 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import random
import re
import time

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    # Flags to fix conflict between payment_reference compute method
    # and onchanges:
    # changing payment_reference via onchange if doesn't work since compute
    # takes the older value in certain conditions, hence we perform all changes in
    # the compute function via the flags that have been set in the onchange methods.
    invoice_date_changed = fields.Boolean(store=False)
    journal_partner_changed = fields.Boolean(store=False)

    def _compute_payment_reference(self):
        """
        payment_reference is stored, computed without api.depends,
        hence we need to manually add triggers for the compute
        cf. self.env.add_to_compute()
        """
        for rec in self:
            if rec.journal_partner_changed:
                rec._onchange_journal_partner_payment_reference()
            if rec.invoice_date_changed:
                rec._onchange_invoice_date_payment_reference()
            if (
                not rec.payment_reference
                and rec.journal_id.invoice_reference_model == "partner"
            ):
                # use case: compute triggered by create() or _post()
                rec._onchange_journal_partner_payment_reference()
            else:
                super(AccountMove, rec)._compute_payment_reference()
        return

    @api.constrains(
        "move_type",
        "partner_id",
        "journal_id",
        "state",
        "payment_reference",
    )
    def _check_customer_invoice_bbacomm(self):
        """
        Adapt this method if you want to use a fixed OGM-VCS per customer.
        """
        for move in self.filtered(
            lambda m: m.state == "posted"
            and m.move_type == "out_invoice"
            and m._is_bbacomm_invoice()
        ):
            payref = move.payment_reference
            payref = payref and payref.strip() or ""
            if payref[:3] == payref[-3:] == "+++":
                # The inverse function on the payment_reference field
                # allows the end user to change the pre-generated OGM/VCS.
                # We assume that a manually entered payment reference is a
                # OGM/VCS when the string starts and ends with '+++'
                payref = self._format_bbacomm(payref)
                if not move._check_bbacomm(payref):
                    raise UserError(
                        message=_(
                            "The OGM-VCS Structured Communication "
                            "is not correctly defined !"
                        )
                    )
            dup_bba_invoice_ids = self._get_objects_with_duplicate_bba(payref)
            if dup_bba_invoice_ids:
                raise UserError(
                    _(
                        "The OGM-VCS Structured Communication has already been used!"
                        "\nPlease use a unique OGM-VCS Payment Communication."
                    )
                )

    @api.onchange("partner_id")
    def _onchange_partner_trigger_compute_payment_reference(self):
        if self.move_type == "out_invoice":
            self.env.add_to_compute(self._fields["payment_reference"], self)

    @api.onchange("partner_id", "journal_id")
    def _onchange_partner_or_journal_set_flag(self):
        if self.move_type == "out_invoice":
            self.journal_partner_changed = True

    def _onchange_journal_partner_payment_reference(self):
        """
        Called from _compute_payment_reference via flags set
        in the onchange method.
        """
        if self.move_type != "out_invoice":
            return
        self.journal_partner_changed = False
        self.payment_reference = False
        if not self.partner_id or not self.journal_id:
            return
        if self._is_bbacomm_invoice():
            self.payment_reference = self._generate_bbacomm()
        else:
            cp = self.partner_id.commercial_partner_id
            if self.journal_id.invoice_reference_model == "partner":
                standard = cp.out_inv_comm_standard
                if standard == "odoo":
                    based_on = cp.invoice_reference_type_odoo
                    if (
                        based_on == "none"
                        or based_on == "invoice"
                        and (not self.name or self.name == "/")
                    ):
                        self.payment_reference = False
                        return
                else:
                    based_on = cp.invoice_reference_type

                if based_on == "invoice":
                    if not self.ids:
                        return
                    ref_function = getattr(
                        self._origin,
                        f"_get_invoice_reference_{standard}_{based_on}",
                        None,
                    )
                else:
                    ref_function = getattr(
                        self, f"_get_invoice_reference_{standard}_{based_on}", None
                    )
                if ref_function is None:
                    raise UserError(
                        _(
                            "The combination of Communication Standard and Algorithm "
                            "on the Curstomer record is not implemented"
                        )
                    )
                self.payment_reference = ref_function()
            else:
                if self.journal_id.invoice_reference_type == "invoice":
                    if not self.ids:
                        return
                    self.payment_reference = (
                        self._origin._get_invoice_computed_reference()
                    )
                else:
                    self.payment_reference = self._get_invoice_computed_reference()

    @api.onchange("invoice_date")
    def _onchange_invoice_date_set_flag(self):
        if self.move_type == "out_invoice":
            self.invoice_date_changed = True
            self.env.add_to_compute(self._fields["payment_reference"], self)

    def _onchange_invoice_date_payment_reference(self):
        """
        Called from _compute_payment_reference via flags set
        in the onchange method.
        """
        if self.move_type != "out_invoice":
            return
        if self.journal_id.invoice_reference_type == "partner" and not self.partner_id:
            return

        self.invoice_date_changed = False
        if self.journal_id.invoice_reference_model != "partner":
            if self._is_bbacomm_invoice():
                self.payment_reference = self._generate_bbacomm()
                return
            elif self.journal_id.invoice_reference_type == "invoice":
                if not self.ids:
                    return
                self.payment_reference = self._origin._get_invoice_computed_reference()
            else:
                self.payment_reference = self._get_invoice_computed_reference()
            return
        cp = self.commercial_partner_id
        if (
            cp.out_inv_comm_standard == "odoo"
            and cp.invoice_reference_type_odoo == "invoice"
            and self.name == "/"
        ):
            self.payment_reference = False
            return
        if (
            not self.invoice_date
            or (
                self.payment_reference
                and not self._check_bbacomm(self.payment_reference)
            )
            or self.journal_id.invoice_reference_model != "partner"
            or (
                self.journal_id.invoice_reference_model == "partner"
                and cp.out_inv_comm_standard != "be"
                and cp.out_inv_comm_algorithm != "date"
            )
        ):
            return
        self.payment_reference = self._generate_bbacomm()

    @api.model_create_multi
    def create(self, vals_list):
        recs = super().create(vals_list)
        for rec in recs:
            if rec.move_type == "out_invoice" and not rec.payment_reference:
                rec._compute_payment_reference()
        return recs

    def write(self, vals):
        res = super().write(vals)
        if "payment_reference" not in vals:
            return res
        for rec in self:
            if rec.move_type in ("out_invoice", "out_refund") and rec.state == "posted":
                if rec.payment_reference != vals["payment_reference"]:
                    raise UserError(
                        _(
                            "You are not allowed to modify the Payment Reference of a posted "
                            "Customer Invoice."
                        )
                    )

    @api.returns("self", lambda value: value.id)
    def copy(self, default=None):
        record = super().copy(default)
        record._onchange_journal_partner_payment_reference()
        return record

    def _get_invoice_reference_odoo_partner(self):
        """
        Replace this method from account/models/account_move.py
        to drop the prefix as well as the str(id) since this is
        not very meaningfull for the end user.
        """
        return self.partner_id.ref

    def _is_bbacomm_invoice(self):
        """
        Returns True when OGM-VCS payment communication will
        be generated for the invoice.
        """
        res = False
        cp = self.commercial_partner_id
        if (
            self.journal_id.invoice_reference_model == "partner"
            and cp.out_inv_comm_standard == "be"
        ):
            res = True
        elif (
            self.journal_id.invoice_reference_model == "be"
            and self.journal_id.invoice_reference_type != "none"
        ):
            res = True
        return res

    def _format_bbacomm(self, val):
        bba = re.sub(r"\D", "", val)
        bba = "+++{}/{}/{}+++".format(bba[0:3], bba[3:7], bba[7:])
        return bba

    def _generate_bbacomm(self, algorithm=None):
        if not algorithm:
            cp = self.commercial_partner_id
            algorithm = "random"
            if (
                self.journal_id.invoice_reference_model == "partner"
                and cp.out_inv_comm_standard == "be"
            ):
                algorithm = cp.out_inv_comm_algorithm
            elif self.journal_id.invoice_reference_model == "be":
                algorithm = self.journal_id.invoice_reference_type
                if algorithm == "partner":
                    algorithm = "partner_ref"
        ref_function = getattr(self, f"_generate_bbacomm_{algorithm}", None)
        if ref_function is None:
            raise UserError(
                _(
                    "The combination of reference model and "
                    "reference type on the journal is not implemented"
                )
            )
        return ref_function()

    def _generate_bbacomm_date(self, date=None):
        docdate = date or self.invoice_date
        if docdate:
            doy = seq = "%03d" % docdate.timetuple().tm_yday
            year = str(docdate.year)
        else:
            doy = time.strftime("%j")
            year = time.strftime("%Y")
        seq = "001"
        previous = self.search(
            [
                ("move_type", "=", "out_invoice"),
                "|",
                ("journal_id.invoice_reference_model", "=", "be"),
                ("partner_id.out_inv_comm_standard", "=", "be"),
                ("payment_reference", "like", "+++{}/{}/%".format(doy, year)),
            ],
            order="payment_reference desc",
            limit=1,
        )
        if previous:
            prev_seq = int(previous[0].payment_reference[12:15])
            if prev_seq < 999:
                seq = "%03d" % (prev_seq + 1)
            else:
                raise UserError(
                    _(
                        "The daily maximum of outgoing invoices "
                        "with an automatically generated "
                        "Belgian OGM-VCS Structured Communication "
                        "has been exceeded!"
                        "\nPlease create manually a unique "
                        "OGM-VCS Structured Communication."
                    )
                )
        bbacomm = doy + year + seq
        base = int(bbacomm)
        mod = base % 97 or 97
        return "+++%s/%s/%s%02d+++" % (doy, year, seq, mod)

    def _generate_bbacomm_partner_ref(self, partner=None):
        partner = partner or self.partner_id.commercial_partner_id
        partner_ref = partner and partner.ref or ""
        partner_ref_nr = re.sub(r"\D", "", partner_ref or "")
        if (len(partner_ref_nr) < 3) or (len(partner_ref_nr) > 7):
            raise UserError(
                _(
                    "The Partner should have a 3-7 digit "
                    "Reference Number for the generation of "
                    "Belgian OGM-VCS Structured Communications with "
                    "Communication Algorithm set to 'Customer Reference' !' \
                  '\nPlease correct the Partner record."
                )
            )
        else:
            partner_ref_nr = partner_ref_nr.ljust(7, "0")
            seq = "001"
            previous = self.search(
                [
                    ("move_type", "=", "out_invoice"),
                    (
                        "payment_reference",
                        "like",
                        "+++{}/{}/%+++".format(partner_ref_nr[:3], partner_ref_nr[3:]),
                    ),
                ],
                order="payment_reference desc",
                limit=1,
            )
            if previous:
                prev_seq = int(previous[0].payment_reference[12:15])
                if prev_seq < 999:
                    seq = "%03d" % (prev_seq + 1)
                else:
                    raise UserError(
                        _(
                            "The daily maximum of outgoing invoices with an "
                            "automatically generated Belgian OGM-VCS "
                            "Structured Communication has been exceeded!"
                            "\nPlease create manually a unique"
                            "OGM-VCS Structured Communication or change the "
                            "Communication Algorithm on the partner record."
                        )
                    )
        bbacomm = partner_ref_nr + seq
        base = int(bbacomm)
        mod = base % 97 or 97
        return "+++%s/%s/%s%02d+++" % (
            partner_ref_nr[:3],
            partner_ref_nr[3:],
            seq,
            mod,
        )

    def _generate_bbacomm_random(self):
        base = random.randint(1, 9999999999)
        bbacomm = str(base).rjust(10, "0")
        base = int(bbacomm)
        mod = base % 97 or 97
        mod = str(mod).rjust(2, "0")
        bbacomm = "+++{}/{}/{}{}+++".format(bbacomm[:3], bbacomm[3:7], bbacomm[7:], mod)
        if self._get_objects_with_duplicate_bba(bbacomm):
            # generate new bbacom to cope with duplicate bba from random generator
            bbacomm = self._generate_bbacomm_random()
        return bbacomm

    def _generate_bbacomm_invoice(self):
        base = self.ids and self.ids[0]
        if not base:
            return
        bbacomm = str(base).rjust(10, "0")
        base = int(bbacomm)
        mod = base % 97 or 97
        mod = str(mod).rjust(2, "0")
        return "+++{}/{}/{}{}+++".format(bbacomm[:3], bbacomm[3:7], bbacomm[7:], mod)

    def _get_objects_with_duplicate_bba(self, bbacomm):
        """
        Inherit this method to detect duplicate OGM_VCS on documents
        such as Sale Orders, Payment Reminders, ...
        """
        dup_ids = []
        if self._name == "account.move":
            dup_dom = self._get_duplicate_bba_domain(bbacomm)
            dup_ids = self._search(dup_dom, limit=1)._result
        return dup_ids

    def _get_duplicate_bba_domain(self, bbacomm):
        dom = [
            ("move_type", "=", "out_invoice"),
            ("state", "!=", "draft"),
            "|",
            ("journal_id.invoice_reference_model", "=", "be"),
            ("commercial_partner_id.out_inv_comm_standard", "=", "bba"),
            ("payment_reference", "=", bbacomm),
            ("id", "not in", self.ids),
        ]
        return dom

    def _check_bbacomm(self, payment_reference):
        supported_chars = "0-9+*/ "
        pattern = re.compile("[^" + supported_chars + "]")
        if pattern.findall(payment_reference or ""):
            return False
        bbacomm = re.sub(r"\D", "", payment_reference or "")
        if len(bbacomm) == 12:
            base = int(bbacomm[:10])
            mod = base % 97 or 97
            if mod == int(bbacomm[-2:]):
                return True
        return False
