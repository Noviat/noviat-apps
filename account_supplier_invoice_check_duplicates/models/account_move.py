# Copyright 2009-2023 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import _, api, fields, models
from odoo.exceptions import RedirectWarning


class AccountMove(models.Model):
    _inherit = "account.move"

    force_encoding = fields.Boolean(
        copy=False,
        readonly=True,
        states={"draft": [("readonly", False)]},
        help="Accept the encoding of this invoice although "
        "it looks like a duplicate.",
    )

    @api.depends("ref", "move_type", "partner_id", "invoice_date", "payment_reference")
    def _compute_duplicated_ref_ids(self):
        """
        Inherit the standard addons _compute_duplicated_ref_ids
        to add payment_reference field in @api.depends of the method.
        """
        return super()._compute_duplicated_ref_ids()

    @api.constrains(
        "ref",
        "move_type",
        "partner_id",
        "journal_id",
        "invoice_date",
        "state",
        "payment_reference",
    )
    def _check_duplicate_supplier_reference(self):
        """
        Replace the standard addons _check_duplicate_supplier_reference
        since this one is too restrictive (blocking) for certain use cases.
        """
        for move in self:
            if (
                move.state == "posted"
                and move.is_purchase_document()
                and not move.force_encoding
            ):
                duplicated_invoices = move._get_duplicated_supplier_invoices(
                    only_posted=True
                )
                if duplicated_invoices:
                    duplicated_moves = move + duplicated_invoices
                    action = self.env["ir.actions.actions"]._for_xml_id(
                        "account.action_move_line_form"
                    )
                    action["domain"] = [("id", "in", duplicated_moves.ids)]
                    action["views"] = [
                        (
                            (view_id, "list")
                            if view_type == "tree"
                            else (view_id, view_type)
                        )
                        for view_id, view_type in action["views"]
                    ]
                    raise RedirectWarning(
                        message=_(
                            "Duplicated vendor reference detected. You probably encoded twice "
                            "the same vendor bill/credit note. Duplicate invoice(s): %s."
                            "\nCheck 'Force Encoding' when this is not a duplicate."
                        )
                        % ", ".join([dup.name for dup in duplicated_invoices]),
                        action=action,
                        button_text=_("Open list"),
                    )

    def _get_duplicated_supplier_invoice_domain(self, only_posted=False):
        """
        Override this method to customize customer specific
        duplicate check query.
        """
        domain = [
            ("move_type", "=", self.move_type),
            ("commercial_partner_id", "=", self.commercial_partner_id.id),
            ("company_id", "=", self.company_id.id),
            ("id", "not in", self.ids),
        ]
        if only_posted:
            domain = domain + [("state", "=", "posted")]
        else:
            domain = domain + [("state", "!=", "cancel")]
        return domain

    def _get_duplicated_supplier_invoice_domain_extra(self):
        """
        Extra search term to detect duplicates in case no
        supplier invoice number has been specified.
        """
        return [
            ("invoice_date", "=", self.invoice_date),
            ("amount_total", "=", self.amount_total),
        ]

    def _get_duplicated_supplier_invoices(self, only_posted=False):
        """
        Override this method to customize customer specific
        duplicate check logic
        """
        domain = self._get_duplicated_supplier_invoice_domain(only_posted=only_posted)

        if self.ref:
            dom_dups = domain + [("ref", "ilike", self.ref)]
        elif self.payment_reference:
            dom_dups = domain + [("payment_reference", "ilike", self.payment_reference)]
        else:
            dom_dups = domain + self._get_duplicated_supplier_invoice_domain_extra()
        return self.search(dom_dups)

    def _fetch_duplicate_supplier_reference(self, only_posted=False):
        """
        Replace the standard addons _fetch_duplicate_supplier_reference
        to have the same behavior everywhere.
        """
        duplicated_invoices = {}
        for move in self.filtered(lambda m: m.is_purchase_document()):
            duplicated_invoices[move] = move._get_duplicated_supplier_invoices(
                only_posted=only_posted
            ).ids
        return duplicated_invoices
