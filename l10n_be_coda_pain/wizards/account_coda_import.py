# Copyright 2009-2023 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import _, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# TODO: Add more keys (e.g. direct debit)
_TRANSACTION_KEYS = [("0", "01", "01", "000"), ("8", "41", "01", "100")]


class AccountCodaImport(models.TransientModel):
    _inherit = "account.coda.import"

    def _match_payment_reference(
        self, wiz_dict, st_line, cba, transaction, reconcile_note
    ):
        """
        Check payment reference in bank statement line
        against payment order lines.
        """
        match = transaction["matching_info"]

        if match["status"] in ["break", "done"]:
            return reconcile_note
        if self._skip_payment_reference_match(
            wiz_dict, st_line, cba, transaction, reconcile_note
        ):
            return reconcile_note

        bankpaylines = self.env["bank.payment.line"].search(
            [("name", "=", transaction["payment_reference"])]
        )
        if bankpaylines:
            if len(bankpaylines) == 1:
                # we do not use the 'bank_payment_line_id' entry
                # in the matching_info at this point in time but
                # we store it to facilitate bug fixing
                match["bank_payment_line_id"] = bankpaylines.id
                paylines = bankpaylines.payment_line_ids
                if paylines:
                    reconcile_note = self._match_payment_line(
                        wiz_dict, st_line, cba, transaction, paylines, reconcile_note
                    )
            else:
                err_string = (
                    _(
                        "\nThe CODA parsing detected a "
                        "payment reference ambiguity while processing "
                        "movement data record 2.3, ref %s!"
                        "\nPlease check your Payment Gateway configuration "
                        "or contact your Odoo support channel."
                    )
                    % transaction["ref"]
                )
                raise UserError(err_string)

        return reconcile_note

    def _match_payment_line(
        self, wiz_dict, st_line, cba, transaction, paylines, reconcile_note
    ):
        """
        Remark:
        We do not check on matching amounts in the case of a payment order,
        hence reconciles can be partial.

        The following process takes place when multiple journal items in
        a payment order are reconciled against the transfer account:

        We may have multiple bank statements lines with the same counterpart
        journal item on the transfer account if the 'group_lines'
        option is not set.
        Partial reconciles are made while processing the statement lines until
        the last statement line corresponding to the payment order has been
        processed. This one results in a full reconcile of the transfer
        account journal item.
        """
        match = transaction["matching_info"]
        match["status"] = "done"
        match["partner_id"] = paylines[0].partner_id.id
        amt_paid = transaction["amount"]
        pain_pm = st_line.journal_id.outbound_payment_method_line_ids.filtered(
            lambda r: r.code == "sepa_credit_transfer"
        )
        transfer_account = (
            pain_pm and pain_pm[0].payment_account_id or self.env["account.account"]
        )
        # In Odoo 13.0 the transfer booking journal could be configured
        # The OCA bank-payment team decided to drop this option in 14.0
        # I am not sure if this was a good idea.
        # Working with transfer account in combination with the Noviat CODA modules
        # will create conflicting journal entry numbers because of the regex logic.
        # So far this doesn't cause issues since our customers usually
        # run with the OCA Payment Order module and we tend to configure
        # the payment mode without transfer booking.
        # Restoring the transfer_journal option is a way to fix this when
        # using the OCA Payment Order but will not work with the Odoo OE
        # Batch Payments.
        # payment_mode = paylines[0].order_id.payment_mode_id
        # transfer_journal = payment_mode.transfer_journal_id
        transfer_journal = st_line.journal_id

        transfer_aml = self.env["account.move.line"]
        counterpart_amls = []

        # Case 1: transfer booking
        for payline in paylines:
            aml = payline.move_line_id
            rec_amls = aml.full_reconcile_id.reconciled_line_ids
            cp_aml = rec_amls.filtered(lambda r: r.journal_id == transfer_journal)
            transfer_aml = cp_aml.move_id.line_ids.filtered(
                lambda r: r.account_id == transfer_account
            )
            if transfer_aml:
                counterpart_amls += [(transfer_aml, -transfer_aml.balance)]
                break

        # Case 2: no transfer booking
        if not transfer_aml:
            check_amt_paid = 0.0
            aml_currencies = self.env["res.currency"]
            for payline in paylines:
                aml = payline.move_line_id
                aml_currencies |= aml.currency_id
                if aml.account_id.internal_type not in ("receivable", "payable"):
                    continue
                check_amt_paid -= payline.amount_currency
                # counterpart_amls += [(aml, aml_amt_paid_ccur)]
                counterpart_amls += [(aml, -payline.amount_currency)]

            if not all(
                [x[1] for x in counterpart_amls]
            ) or not payline.currency_id.is_zero(amt_paid - check_amt_paid):
                counterpart_amls = []
        match["counterpart_amls"] = counterpart_amls
        return reconcile_note

    def _skip_payment_reference_match(
        self, wiz_dict, st_line, cba, transaction, reconcile_note
    ):
        skip = False
        if not transaction["payment_reference"]:
            skip = True
        if not cba.find_payment:
            skip = True
        if transaction["amount"] >= 0.0:
            skip = True

        matching_key = False
        for k in _TRANSACTION_KEYS:
            if (
                k[0] == transaction["trans_type"]
                and k[1] == transaction["trans_family"]
                and k[2] == transaction["trans_code"]
                and k[3] == transaction["trans_category"]
            ):
                matching_key = True
                break
        if not matching_key:
            skip = True

        return skip
