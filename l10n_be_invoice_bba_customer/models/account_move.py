# Copyright 2009-2020 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import random
import re
import time

from odoo import _, api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    def check_bbacomm(self, val):
        supported_chars = "0-9+*/ "
        pattern = re.compile("[^" + supported_chars + "]")
        if pattern.findall(val or ""):
            return False
        bbacomm = re.sub(r"\D", "", val or "")
        if len(bbacomm) == 12:
            base = int(bbacomm[:10])
            mod = base % 97 or 97
            if mod == int(bbacomm[-2:]):
                return True
        return False

    def duplicate_bba(self, partner, invoice_payment_ref):
        """
        overwrite this method to customize the handling of
        duplicate BBA communications
        """
        if partner.out_inv_comm_algorithm == "random":
            # generate new bbacom to cope with duplicate bba coming
            # out of random generator
            invoice_payment_ref = self.generate_bbacomm(partner)

        dups = self.search(
            [
                ("type", "=", "out_invoice"),
                ("state", "!=", "draft"),
                ("partner_id.out_inv_comm_type", "=", "bba"),
                ("invoice_payment_ref", "=", invoice_payment_ref),
            ]
        )
        if dups:
            raise UserError(
                _(
                    "The BBA Structured Communication "
                    "has already been used!"
                    "\nPlease use a unique BBA Structured Communication."
                )
            )
        return invoice_payment_ref

    @api.onchange("partner_id", "company_id")
    def _onchange_partner_id(self):
        res = super()._onchange_partner_id()
        partner = self.partner_id.commercial_partner_id
        if self.type == "out_invoice":
            if partner.out_inv_comm_type == "bba":
                self.invoice_payment_ref = self.generate_bbacomm(partner)
        return res

    def format_bbacomm(self, val):
        bba = re.sub(r"\D", "", val)
        bba = "+++{}/{}/{}+++".format(bba[0:3], bba[3:7], bba[7:])
        return bba

    def _generate_bbacomm_hook(self, partner, algorithm):
        """
        hook to add customer specific algorithm
        """
        raise UserError(
            _(
                "Unsupported Structured Communication Type "
                "Algorithm '%s' !"
                "\nPlease contact your Odoo support channel."
            )
            % algorithm
        )

    def generate_bbacomm(self, partner):
        algorithm = "random"
        if partner:
            algorithm = partner.out_inv_comm_algorithm or "random"
        else:
            partner = False

        if algorithm == "date":
            doy = time.strftime("%j")
            year = time.strftime("%Y")
            seq = "001"
            sequences = self.search(
                [
                    ("type", "=", "out_invoice"),
                    ("partner_id.out_inv_comm_type", "=", "bba"),
                    ("invoice_payment_ref", "like", "+++{}/{}/%".format(doy, year)),
                ],
                order="invoice_payment_ref",
            )
            if sequences:
                prev_seq = int(sequences[-1].reference[12:15])
                if prev_seq < 999:
                    seq = "%03d" % (prev_seq + 1)
                else:
                    raise UserError(
                        _(
                            "The daily maximum of outgoing invoices "
                            "with an automatically generated "
                            "BBA Structured Communication "
                            "has been exceeded!"
                            "\nPlease create manually a unique "
                            "BBA Structured Communication."
                        )
                    )
            bbacomm = doy + year + seq
            base = int(bbacomm)
            mod = base % 97 or 97
            invoice_payment_ref = "+++%s/%s/%s%02d+++" % (doy, year, seq, mod)

        elif algorithm == "partner_ref":
            partner_ref = partner and partner.ref
            partner_ref_nr = re.sub(r"\D", "", partner_ref or "")
            if (len(partner_ref_nr) < 3) or (len(partner_ref_nr) > 7):
                raise UserError(
                    _(
                        "The Partner should have a 3-7 digit "
                        "Reference Number for the generation of "
                        "BBA Structured Communications!' \
                      '\nPlease correct the Partner record."
                    )
                )
            else:
                partner_ref_nr = partner_ref_nr.ljust(7, "0")
                seq = "001"
                sequences = self.search(
                    [
                        ("type", "=", "out_invoice"),
                        ("partner_id.out_inv_comm_type", "=", "bba"),
                        (
                            "invoice_payment_ref",
                            "like",
                            "+++{}/{}/%".format(partner_ref_nr[:3], partner_ref_nr[3:]),
                        ),
                    ],
                    order="invoice_payment_ref",
                )
                if sequences:
                    prev_seq = int(sequences[-1].reference[12:15])
                    if prev_seq < 999:
                        seq = "%03d" % (prev_seq + 1)
                    else:
                        raise UserError(
                            _(
                                "The daily maximum of outgoing "
                                "invoices with an automatically "
                                "generated BBA Structured "
                                "Communications has been exceeded!"
                                "\nPlease create manually a unique"
                                "BBA Structured Communication."
                            )
                        )
            bbacomm = partner_ref_nr + seq
            base = int(bbacomm)
            mod = base % 97 or 97
            invoice_payment_ref = "+++%s/%s/%s%02d+++" % (
                partner_ref_nr[:3],
                partner_ref_nr[3:],
                seq,
                mod,
            )

        elif algorithm == "random":
            base = random.randint(1, 9999999999)
            bbacomm = str(base).rjust(10, "0")
            base = int(bbacomm)
            mod = base % 97 or 97
            mod = str(mod).rjust(2, "0")
            invoice_payment_ref = "+++{}/{}/{}{}+++".format(
                bbacomm[:3], bbacomm[3:7], bbacomm[7:], mod
            )

        else:
            invoice_payment_ref = self._generate_bbacomm_hook(partner, algorithm)

        return invoice_payment_ref

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            inv_type = vals.get("type") or self.env.context.get("default_type")
            if inv_type != "out_invoice":
                continue

            partner = self.env["res.partner"].browse(vals.get("partner_id"))
            partner = partner.commercial_partner_id
            reference_type = partner.out_inv_comm_type
            if reference_type != "bba":
                continue

            payref = vals.get("invoice_payment_ref")
            if not self.check_bbacomm(payref):
                payref = self.generate_bbacomm(partner)
                dups = self.search(
                    [
                        ("type", "=", "out_invoice"),
                        ("state", "!=", "draft"),
                        ("partner_id.out_inv_comm_type", "=", "bba"),
                        ("invoice_payment_ref", "=", payref),
                    ]
                )
                if dups:
                    payref = self.duplicate_bba(partner, payref)
                vals["invoice_payment_ref"] = payref

        return super().create(vals_list)

    def write(self, vals):
        todo = self.env["account.move"]
        for inv in self:
            inv_type = vals.get("type") or inv.type
            if inv_type != "out_invoice" or inv.state != "draft":
                todo += inv
                continue

            if vals.get("partner_id"):
                partner = self.env["res.partner"].browse(vals["partner_id"])
            else:
                partner = inv.partner_id
            partner = partner.commercial_partner_id
            reference_type = partner.out_inv_comm_type
            if reference_type != "bba":
                todo += inv
                continue

            payref = vals.get("invoice_payment_ref") or inv.invoice_payment_ref
            if not self.check_bbacomm(payref):
                payref = self.generate_bbacomm(partner)
                dups = self.search(
                    [
                        ("id", "!=", inv.id),
                        ("type", "=", "out_invoice"),
                        ("state", "!=", "draft"),
                        ("partner_id.out_inv_comm_type", "=", "bba"),
                        ("invoice_payment_ref", "=", payref),
                    ]
                )
                if dups:
                    payref = self.duplicate_bba(partner, payref)
            if payref != inv.invoice_payment_ref:
                vals2 = vals.copy()
                vals2["invoice_payment_ref"] = payref
                super(AccountMove, inv).write(dict(vals, invoice_payment_ref=payref))
            else:
                todo += inv
        return super(AccountMove, todo).write(vals)

    @api.returns("self", lambda value: value.id)
    def copy(self, default=None):
        default = default or {}
        if self.type == "out_invoice":
            partner = self.partner_id.commercial_partner_id
            reference_type = partner.out_inv_comm_type
            if reference_type == "bba":
                default["invoice_payment_ref"] = self.generate_bbacomm(partner)
        return super().copy(default)
