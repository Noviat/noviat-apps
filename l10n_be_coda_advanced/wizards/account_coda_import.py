# Copyright 2009-2023 Noviat.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import base64
import json
import logging
import re
import time
import zipfile
from io import BytesIO
from itertools import combinations
from sys import exc_info
from traceback import format_exception

from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval

from .coda_helpers import (
    calc_iban_checksum,
    check_bban,
    check_iban,
    get_iban_and_bban,
    list2float,
    number2float,
    repl_special,
    str2date,
    str2time,
)

_logger = logging.getLogger(__name__)

# TODO: Add more keys (e.g. direct debit)
TRANSACTION_KEYS = [("0", "01", "01", "000"), ("8", "41", "01", "100")]

INDENT4 = "\n" + 4 * " "
INDENT8 = "\n" + 8 * " "
INDENT4_HTML = "<br>" + 4 * "&nbsp;"
INDENT8_HTML = "<br>" + 4 * "&nbsp;"
ST_LINE_NAME_FAMILIES = ["13", "35", "41", "80"]
PARSE_COMMS_MOVE = [
    "100",
    "101",
    "102",
    "103",
    "105",
    "106",
    "107",
    "108",
    "111",
    "113",
    "114",
    "115",
    "121",
    "122",
    "123",
    "124",
    "125",
    "126",
    "127",
]
PARSE_COMMS_INFO = [
    "001",
    "002",
    "004",
    "005",
    "006",
    "007",
    "008",
    "009",
    "010",
    "011",
]


class AccountCodaImport(models.TransientModel):
    _name = "account.coda.import"
    _description = "Import CODA File"

    coda_data = fields.Binary(string="CODA (Zip) File", required=True)
    coda_fname = fields.Char(string="CODA Filename", default="", required=True)
    accounting_date = fields.Date(help="Keep empty to use the date in the CODA File")
    reconcile = fields.Boolean(
        help="Launch Automatic Reconcile after CODA import.", default=True
    )
    reconcile_matching_details = fields.Boolean(
        help="Show details of the transaction and partner lookup "
        "when the lookup does not result in a match.",
    )
    skip_undefined = fields.Boolean(
        help="Skip Bank Statements for accounts which have not been defined "
        "in the CODA configuration.",
        default=True,
    )
    note = fields.Text(string="Log")

    @api.model
    def _check_account_payment(self, wiz_dict):
        res = self.env["ir.module.module"].search(
            [("name", "=", "account_payment"), ("state", "=", "installed")]
        )
        return res and True or False

    def _coda_record_0(self, wiz_dict, coda_statement, line, coda_parsing_note):

        coda_version = line[127]
        if coda_version not in ["1", "2"]:
            err_string = (
                _(
                    "\nCODA V%s statements are not supported, "
                    "please contact your bank !"
                )
                % coda_version
            )
            raise UserError(err_string)
        coda_statement["coda_version"] = coda_version
        coda_statement["coda_transactions"] = {}
        coda_statement["date"] = str2date(line[5:11])
        coda_statement["coda_creation_date"] = str2date(line[5:11])
        coda_statement["bic"] = line[60:71].strip()
        coda_statement["separate_application"] = line[83:88]
        coda_statement["first_transaction_date"] = False
        coda_statement["state"] = "draft"
        coda_statement["coda_note"] = ""
        coda_statement["skip"] = False
        coda_statement["main_move_stack"] = []
        coda_statement["glob_lvl_stack"] = [0]
        return coda_parsing_note

    def _coda_record_1(  # noqa: C901
        self, wiz_dict, coda_statement, line, coda_parsing_note
    ):
        skip = False
        coda_statement["currency"] = "EUR"  # default currency
        if coda_statement["coda_version"] == "1":
            coda_statement["acc_number"] = line[5:17]
            if line[18:21].strip():
                coda_statement["currency"] = line[18:21]
        elif line[1] == "0":  # Belgian bank account BBAN structure
            coda_statement["acc_number"] = line[5:17]
            coda_statement["currency"] = line[18:21]
        elif line[1] == "1":  # foreign bank account BBAN structure
            coda_statement["acc_number"] = line[5:39].strip()
            coda_statement["currency"] = line[39:42]
        elif line[1] == "2":  # Belgian bank account IBAN structure
            coda_statement["acc_number"] = line[5:21]
            coda_statement["currency"] = line[39:42]
        elif line[1] == "3":  # foreign bank account IBAN structure
            coda_statement["acc_number"] = line[5:39].strip()
            coda_statement["currency"] = line[39:42]
        else:
            err_string = _("\nUnsupported bank account structure !")
            raise UserError(err_string)
        coda_statement["description"] = line[90:125].strip()

        def cba_filter(coda_bank):
            acc_number = coda_bank.bank_id.sanitized_acc_number
            if acc_number:
                cba_numbers = get_iban_and_bban(acc_number)
                cba_currency = coda_bank.currency_id.name
                cba_descriptions = [
                    coda_bank.description1 or "",
                    coda_bank.description2 or "",
                ]
                if (
                    coda_statement["acc_number"] in cba_numbers
                    and coda_statement["currency"] == cba_currency
                    and coda_statement["description"] in cba_descriptions
                ):
                    return True
            return False

        cba = wiz_dict["coda_banks"].filtered(cba_filter)
        if cba:
            if cba.company_id not in self.env.companies:
                wiz_dict["coda_import_note"] += _(
                    "\n\nMatching CODA Bank Account Configuration "
                    "record found for Bank Account Number '%(number)s' "
                    "in Company %(company)s !"
                    "\nPlease switch to this Company in order "
                    "to import statements for this Bank Account Number !"
                ) % {
                    "number": coda_statement["acc_number"],
                    "company": cba.company_id.name,
                }
                skip = True
            else:
                # rebrowse to enforce record rules
                cba = self.env["coda.bank.account"].browse(cba.id)
            coda_statement["coda_bank_params"] = cba
            wiz_dict["company_bank_accounts"] = cba.company_id.bank_journal_ids.mapped(
                "bank_account_id"
            ).mapped("sanitized_acc_number")
        else:
            if self.skip_undefined:
                wiz_dict["coda_import_note"] += _(
                    "\n\nNo matching CODA Bank Account Configuration " "record found !"
                ) + _(
                    "\nPlease check if the 'Bank Account Number', "
                    "'Currency' and 'Account Description' fields "
                    "of your configuration record match with"
                    " '%(number)s', '%(currency)s' and '%(description)s' if you need "
                    "to import statements for this Bank Account Number !"
                ) % {
                    "number": coda_statement["acc_number"],
                    "currency": coda_statement["currency"],
                    "description": coda_statement["description"],
                }
                skip = True
            else:
                err_string = _(
                    "\nNo matching CODA Bank Account Configuration " "record found !"
                ) + _(
                    "\nPlease check if the 'Bank Account Number', "
                    "'Currency' and 'Account Description' fields "
                    "of your configuration record match with"
                    " '%(number)s', '%(currency)s' and '%(description)s' !"
                ) % {
                    "number": coda_statement["acc_number"],
                    "currency": coda_statement["currency"],
                    "description": coda_statement["description"],
                }
                raise UserError(err_string)
        bal_start = list2float(line[43:58])  # old balance data
        if line[42] == "1":  # 1= Debit
            bal_start = -bal_start
        coda_statement["balance_start"] = bal_start
        coda_statement["old_balance_date"] = str2date(line[58:64])
        coda_statement["acc_holder"] = line[64:90]
        coda_statement["paper_ob_seq_number"] = line[2:5]
        coda_statement["coda_seq_number"] = line[125:128]

        if skip:
            coda_statement["skip"] = skip
            return coda_parsing_note

        # we already initialise the coda_statement['name'] field
        # with the currently available date
        # in case an 8 record is present, this data will be updated
        coda_statement["name"] = cba.coda_st_naming % {
            "code": cba.journal_id.code or "",
            "year": coda_statement["date"][:4],
            "y": coda_statement["date"][2:4],
            "coda": coda_statement["coda_seq_number"],
            "paper_ob": coda_statement["paper_ob_seq_number"],
            "paper": coda_statement["paper_ob_seq_number"],
        }
        # We have to skip the already processed statements
        # when we reprocess CODA file
        if wiz_dict["coda_id"]:
            old_statements = self.env["account.bank.statement"].search(
                [
                    ("coda_id", "=", wiz_dict["coda_id"]),
                    ("name", "=", coda_statement["name"]),
                ]
            )
            if old_statements:
                skip = True

        # hook to allow further customisation
        if not skip:
            self._coda_statement_init_hook(wiz_dict, coda_statement)
        coda_statement["skip"] = skip

        return coda_parsing_note

    def _coda_record_2(
        self, wiz_dict, coda_statement, line, coda_parsing_note, transaction_seq
    ):

        if line[1] == "1":
            coda_parsing_note, transaction_seq = self._coda_record_21(
                wiz_dict, coda_statement, line, coda_parsing_note, transaction_seq
            )

        elif line[1] == "2":
            coda_parsing_note = self._coda_record_22(
                wiz_dict, coda_statement, line, coda_parsing_note, transaction_seq
            )

        elif line[1] == "3":
            coda_parsing_note = self._coda_record_23(
                wiz_dict, coda_statement, line, coda_parsing_note, transaction_seq
            )

        else:
            # movement data record 2.x (x <> 1,2,3)
            err_string = (
                _("\nMovement data records of type 2.%s are not supported !") % line[1]
            )
            raise UserError(err_string)

        return coda_parsing_note, transaction_seq

    def _coda_record_21(  # noqa: C901
        self, wiz_dict, coda_statement, line, coda_parsing_note, transaction_seq
    ):

        # list of lines parsed already
        coda_transactions = coda_statement["coda_transactions"]

        transaction = {}
        transaction_seq = transaction_seq + 1
        transaction["sequence"] = transaction_seq
        transaction["type"] = "regular"
        transaction["trans_family"] = False
        transaction["struct_comm_type"] = ""
        transaction["struct_comm_type_id"] = False
        transaction["struct_comm_type_desc"] = ""
        transaction["struct_comm_bba"] = ""
        transaction["communication"] = ""
        transaction["payment_reference"] = ""
        transaction["creditor_reference_type"] = ""
        transaction["creditor_reference"] = ""
        transaction["partner_name"] = ""
        transaction["counterparty_bic"] = ""
        transaction["counterparty_number"] = ""
        transaction["counterparty_currency"] = ""
        transaction["glob_lvl_flag"] = False
        transaction["globalisation_amount"] = False
        transaction["amount"] = 0.0

        transaction["ref"] = line[2:10]
        transaction["ref_move"] = line[2:6]
        transaction["ref_move_detail"] = line[6:10]

        main_move_stack = coda_statement["main_move_stack"]
        previous_main_move = main_move_stack and main_move_stack[-1] or False
        main_move_stack_pop = True

        if (
            main_move_stack
            and transaction["ref_move"] != main_move_stack[-1]["ref_move"]
        ):
            # initialise main_move_stack
            # used to link 2.1 detail records to 2.1 main record
            # The main_move_stack contains the globalisation level move
            # or moves (in case of multiple levels)
            # plus the previous transaction move.
            main_move_stack = []
            main_move_stack_pop = False
            coda_statement["main_move_stack"] = main_move_stack
            # initialise globalisation stack
            coda_statement["glob_lvl_stack"] = [0]

        if main_move_stack:
            if main_move_stack[-1]["type"] == "globalisation":
                transaction["glob_sequence"] = main_move_stack[-1]["sequence"]
            elif main_move_stack[-1].get("glob_sequence"):
                transaction["glob_sequence"] = main_move_stack[-1]["glob_sequence"]

        glob_lvl_stack = coda_statement["glob_lvl_stack"]
        glob_lvl_stack_pop = False
        glob_lvl_stack_append = False

        transaction["trans_ref"] = line[10:31]
        transaction_amt = list2float(line[32:47])
        if line[31] == "1":  # 1=debit
            transaction_amt = -transaction_amt

        transaction["trans_type"] = line[53]
        trans_type = [
            x for x in wiz_dict["trans_types"] if transaction["trans_type"] == x.type
        ]
        if not trans_type:
            err_string = (
                _("\nThe File contains an invalid CODA Transaction Type : %s !")
                % transaction["trans_type"]
            )
            raise UserError(err_string)
        transaction["trans_type_id"] = trans_type[0].id
        transaction["trans_type_desc"] = trans_type[0].description

        # processing of amount depending on globalisation
        glob_lvl_flag = int(line[124])
        transaction["glob_lvl_flag"] = glob_lvl_flag
        if glob_lvl_flag > 0:
            if glob_lvl_stack and glob_lvl_stack[-1] == glob_lvl_flag:
                transaction["amount"] = transaction_amt
                glob_lvl_stack_pop = True
            else:
                transaction["type"] = "globalisation"
                transaction["amount"] = 0.0
                transaction["globalisation_amount"] = transaction_amt
                main_move_stack_pop = False
                glob_lvl_stack_append = True
        else:
            transaction["amount"] = transaction_amt
            if previous_main_move and previous_main_move["glob_lvl_flag"] > 0:
                main_move_stack_pop = False

        # The 'globalisation' concept can also be implemented
        # without the globalisation level flag.
        # This is e.g. used by Europabank to give the details of
        # Card Payments.
        if (
            previous_main_move
            and transaction["ref_move"] == previous_main_move["ref_move"]
        ):
            if transaction["ref_move_detail"] == "9999":
                # Current CODA parsing logic doesn't
                # support > 9999 detail lines
                err_string = _("\nTransaction Detail Limit reached !")
                raise UserError(err_string)
            elif transaction["ref_move_detail"] != "0000":
                if (
                    glob_lvl_stack[-1] == 0
                    and previous_main_move["type"] != "globalisation"
                ):
                    # promote associated move record
                    # into a globalisation
                    glob_lvl_flag = 1
                    glob_lvl_stack_append = True
                    k = previous_main_move["sequence"]
                    to_promote = coda_transactions[k]
                    if not previous_main_move.get("detail_cnt"):
                        to_promote.update(
                            {
                                "type": "globalisation",
                                "glob_lvl_flag": glob_lvl_flag,
                                "globalisation_amount": previous_main_move["amount"],
                                "amount": 0.0,
                            }
                        )
                        previous_main_move["promoted"] = True
                    main_move_stack_pop = False
                if not previous_main_move.get("detail_cnt"):
                    previous_main_move["detail_cnt"] = 1
                else:
                    previous_main_move["detail_cnt"] += 1

        # positions 48-53 : Value date or 000000 if not known (DDMMYY)
        transaction["val_date"] = str2date(line[47:53])
        # positions 54-61 : transaction code
        transaction["trans_family"] = line[54:56]
        trans_family = [
            x
            for x in wiz_dict["trans_codes"]
            if (x.type == "family") and (x.code == transaction["trans_family"])
        ]
        if not trans_family:
            err_string = (
                _("\nThe File contains an invalid " "CODA Transaction Family : %s !")
                % transaction["trans_family"]
            )
            raise UserError(err_string)
        trans_family = trans_family[0]
        transaction["trans_family_id"] = trans_family.id
        transaction["trans_family_desc"] = trans_family.description
        transaction["trans_code"] = line[56:58]
        trans_code = [
            x
            for x in wiz_dict["trans_codes"]
            if (x.type == "code")
            and (x.code == transaction["trans_code"])
            and (trans_family.id == x.parent_id.id)
        ]
        if trans_code:
            transaction["trans_code_id"] = trans_code[0].id
            transaction["trans_code_desc"] = trans_code[0].description
        else:
            transaction["trans_code_id"] = None
            transaction["trans_code_desc"] = _(
                "Transaction Code unknown, " "please consult your bank."
            )
        transaction["trans_category"] = line[58:61]
        trans_category = [
            x
            for x in wiz_dict["trans_categs"]
            if transaction["trans_category"] == x.category
        ]
        if trans_category:
            transaction["trans_category_id"] = trans_category[0].id
            transaction["trans_category_desc"] = trans_category[0].description
        else:
            transaction["trans_category_id"] = None
            transaction["trans_category_desc"] = _(
                "Transaction Category unknown, " "please consult your bank."
            )
        # positions 61-115 : communication
        if line[61] == "1":
            transaction["struct_comm_type"] = line[62:65]
            comm_type = [
                x
                for x in wiz_dict["comm_types"]
                if x.code == transaction["struct_comm_type"]
            ]
            if not comm_type:
                err_string = (
                    _(
                        "\nThe File contains an invalid "
                        "Structured Communication Type : %s !"
                    )
                    % transaction["struct_comm_type"]
                )
                raise UserError(err_string)
            transaction["struct_comm_type_id"] = comm_type[0].id
            transaction["struct_comm_type_desc"] = comm_type[0].description
            transaction["communication"] = transaction["name"] = line[65:115]
            if transaction["struct_comm_type"] in ["101", "102"]:
                bbacomm = line[65:77]
                transaction["struct_comm_bba"] = transaction["name"] = (
                    "+++"
                    + bbacomm[0:3]
                    + "/"
                    + bbacomm[3:7]
                    + "/"
                    + bbacomm[7:]
                    + "+++"
                )
                # SEPA SCT <CdtrRefInf> type
                transaction["creditor_reference_type"] = "BBA"
                # SEPA SCT <CdtrRefInf> reference
                transaction["creditor_reference"] = bbacomm
        else:
            transaction["communication"] = transaction["name"] = line[62:115].strip()
        transaction["entry_date"] = str2date(line[115:121])
        if transaction["sequence"] == 1:
            coda_statement["first_transaction_date"] = transaction["entry_date"]
        # positions 122-124 not processed

        # store transaction
        coda_transactions[transaction_seq] = transaction

        if previous_main_move:

            if previous_main_move.get("detail_cnt") and previous_main_move.get(
                "promoted"
            ):
                # add closing globalisation level on previous detail record
                # in order to correctly close moves that have been
                # 'promoted' to globalisation
                closeglobalise = coda_transactions[transaction_seq - 1]
                closeglobalise.update(
                    {"glob_lvl_flag": previous_main_move["glob_lvl_flag"]}
                )
            else:
                # Demote record with globalisation code from
                # 'globalisation' to 'regular' when no detail records.
                # The same logic is repeated on the New Balance Record
                # ('8 Record') in order to cope with CODA files containing
                # a single 2.1 record that needs to be 'demoted'.
                if previous_main_move[
                    "type"
                ] == "globalisation" and not previous_main_move.get("detail_cnt"):
                    # demote record with globalisation code from
                    # 'globalisation' to 'regular' when no detail records
                    k = previous_main_move["sequence"]
                    to_demote = coda_transactions[k]
                    to_demote.update(
                        {
                            "type": "regular",
                            "glob_lvl_flag": 0,
                            "globalisation_amount": False,
                            "amount": previous_main_move["globalisation_amount"],
                        }
                    )

            if main_move_stack_pop:
                main_move_stack.pop()

        main_move_stack.append(transaction)
        if glob_lvl_stack_append:
            glob_lvl_stack.append(glob_lvl_flag)
        if glob_lvl_stack_pop:
            glob_lvl_stack.pop()

        return coda_parsing_note, transaction_seq

    def _coda_record_22(
        self, wiz_dict, coda_statement, line, coda_parsing_note, transaction_seq
    ):

        transaction = coda_statement["coda_transactions"][transaction_seq]
        if transaction["ref"][0:4] != line[2:6]:
            err_string = (
                _(
                    "\nCODA parsing error on movement data record 2.2, seq nr %s!"
                    "\nPlease report this issue via your Odoo support channel."
                )
                % line[2:10]
            )
            raise UserError(err_string)
        comm_extra = line[10:63]
        if not transaction.get("struct_comm_type_id"):
            comm_extra = comm_extra.rstrip()
        transaction["name"] += comm_extra.rstrip()
        transaction["communication"] += comm_extra
        transaction["payment_reference"] = line[63:98].strip()
        transaction["counterparty_bic"] = line[98:109].strip()
        transaction["R_transaction_type"] = line[112].strip()
        transaction["ISO_reason_return_code"] = line[113:117].strip()
        transaction["category_purpose"] = line[117:121].strip()
        transaction["purpose"] = line[121:125].strip()

        return coda_parsing_note

    def _coda_record_23(
        self, wiz_dict, coda_statement, line, coda_parsing_note, transaction_seq
    ):

        transaction = coda_statement["coda_transactions"][transaction_seq]
        if transaction["ref"][0:4] != line[2:6]:
            err_string = (
                _(
                    "\nCODA parsing error on movement data record 2.3, seq nr %s!"
                    "'\nPlease report this issue via your Odoo support channel."
                )
                % line[2:10]
            )
            raise UserError(err_string)

        if coda_statement["coda_version"] == "1":
            counterparty_number = line[10:22].strip()
            counterparty_name = line[47:125].strip()
            counterparty_currency = ""
        else:
            if line[22] == " ":
                counterparty_number = line[10:22].strip()
                counterparty_currency = line[23:26].strip()
            else:
                counterparty_number = line[10:44].strip()
                counterparty_currency = line[44:47].strip()
            counterparty_name = line[47:82].strip()
            comm_extra = line[82:125]
            if not transaction.get("struct_comm_type_id"):
                comm_extra = comm_extra.rstrip()
            transaction["name"] += comm_extra.rstrip()
            transaction["communication"] += comm_extra
        transaction["counterparty_number"] = counterparty_number
        transaction["counterparty_currency"] = counterparty_currency
        transaction["partner_name"] = counterparty_name

        return coda_parsing_note

    def _coda_record_3(
        self, wiz_dict, coda_statement, line, coda_parsing_note, transaction_seq
    ):

        if line[1] == "1":
            coda_parsing_note, transaction_seq = self._coda_record_31(
                wiz_dict, coda_statement, line, coda_parsing_note, transaction_seq
            )

        elif line[1] == "2":
            coda_parsing_note = self._coda_record_32(
                wiz_dict, coda_statement, line, coda_parsing_note, transaction_seq
            )

        elif line[1] == "3":
            coda_parsing_note = self._coda_record_33(
                wiz_dict, coda_statement, line, coda_parsing_note, transaction_seq
            )

        return coda_parsing_note, transaction_seq

    def _coda_record_31(
        self, wiz_dict, coda_statement, line, coda_parsing_note, transaction_seq
    ):

        # list of lines parsed already
        transaction = coda_statement["coda_transactions"][transaction_seq]

        info_line = {}
        info_line["entry_date"] = transaction["entry_date"]
        info_line["type"] = "information"
        transaction_seq = transaction_seq + 1
        info_line["sequence"] = transaction_seq
        info_line["struct_comm_type"] = ""
        info_line["struct_comm_type_desc"] = ""
        info_line["communication"] = ""
        info_line["ref"] = line[2:10]
        info_line["ref_move"] = line[2:6]
        info_line["ref_move_detail"] = line[6:10]
        info_line["trans_ref"] = line[10:31]
        # get key of associated transaction record
        mm_seq = coda_statement["main_move_stack"][-1]["sequence"]
        trans_check = coda_statement["coda_transactions"][mm_seq]["trans_ref"]
        if info_line["trans_ref"] != trans_check:
            err_string = (
                _(
                    "\nCODA parsing error on "
                    "information data record 3.1, seq nr %s !"
                    "\nPlease report this issue via your Odoo support channel."
                )
                % line[2:10]
            )
            raise UserError(err_string)
        info_line["main_move_sequence"] = mm_seq
        # positions 32-38 : transaction code
        info_line["trans_type"] = line[31]
        trans_type = [
            x for x in wiz_dict["trans_types"] if x.type == info_line["trans_type"]
        ]
        if not trans_type:
            err_string = (
                _("\nThe File contains an invalid CODA Transaction Type : %s !")
                % info_line["trans_type"]
            )
            raise UserError(err_string)
        info_line["trans_type_desc"] = trans_type[0].description
        info_line["trans_family"] = line[32:34]
        trans_family = [
            x
            for x in wiz_dict["trans_codes"]
            if (x.type == "family") and (x.code == info_line["trans_family"])
        ]
        if not trans_family:
            err_string = (
                _("\nThe File contains an invalid CODA Transaction Family : %s !")
                % info_line["trans_family"]
            )
            raise UserError(err_string)
        trans_family = trans_family[0]
        info_line["trans_family_desc"] = trans_family.description
        info_line["trans_code"] = line[34:36]
        trans_code = [
            x
            for x in wiz_dict["trans_codes"]
            if (x.type == "code")
            and (x.code == info_line["trans_code"])
            and (x.parent_id.id == trans_family.id)
        ]
        if trans_code:
            info_line["trans_code_desc"] = trans_code[0].description
        else:
            info_line["trans_code_desc"] = _(
                "Transaction Code unknown, please consult your bank."
            )
        info_line["trans_category"] = line[36:39]
        trans_category = [
            x
            for x in wiz_dict["trans_categs"]
            if x.category == info_line["trans_category"]
        ]
        if trans_category:
            info_line["trans_category_desc"] = trans_category[0].description
        else:
            info_line["trans_category_desc"] = _(
                "Transaction Category unknown, please consult your bank."
            )
        # positions 40-113 : communication
        if line[39] == "1":
            info_line["struct_comm_type"] = line[40:43]
            comm_type = [
                x
                for x in wiz_dict["comm_types"]
                if x.code == info_line["struct_comm_type"]
            ]
            if not comm_type:
                err_string = (
                    _(
                        "\nThe File contains an invalid "
                        "Structured Communication Type : %s !"
                    )
                    % info_line["struct_comm_type"]
                )
                raise UserError(err_string)
            info_line["struct_comm_type_desc"] = comm_type[0].description
            info_line["communication"] = line[43:113]
            info_line["name"] = info_line["communication"].strip()
        else:
            name = _("Extra information")
            info = line[40:113]
            info_line["name"] = name + ": " + info
            info_line["communication"] = INDENT8_HTML + name + ":"
            info_line["communication"] += INDENT8_HTML + info
        # positions 114-128 not processed

        # store transaction
        coda_statement["coda_transactions"][transaction_seq] = info_line
        return coda_parsing_note, transaction_seq

    def _coda_record_32(
        self, wiz_dict, coda_statement, line, coda_parsing_note, transaction_seq
    ):

        transaction = coda_statement["coda_transactions"][transaction_seq]
        if transaction["ref_move"] != line[2:6]:
            err_string = (
                _(
                    "\nCODA parsing error on "
                    "information data record 3.2, seq nr %s!"
                    "\nPlease report this issue via your Odoo support channel."
                )
                % transaction["ref"]
            )
            raise UserError(err_string)
        comm_extra = line[10:115]
        if not transaction.get("struct_comm_type_id"):
            comm_extra = comm_extra.rstrip()
        transaction["name"] += comm_extra.rstrip()
        transaction["communication"] += comm_extra

        return coda_parsing_note

    def _coda_record_33(
        self, wiz_dict, coda_statement, line, coda_parsing_note, transaction_seq
    ):

        transaction = coda_statement["coda_transactions"][transaction_seq]
        if transaction["ref_move"] != line[2:6]:
            err_string = (
                _(
                    "\nCODA parsing error on "
                    "information data record 3.3, seq nr %s !"
                    "\nPlease report this issue via your Odoo support channel."
                )
                % line[2:10]
            )
            raise UserError(err_string)
        comm_extra = line[10:100].rstrip()
        transaction["name"] += comm_extra
        transaction["communication"] += comm_extra

        return coda_parsing_note

    def _coda_record_4(
        self, wiz_dict, coda_statement, line, coda_parsing_note, transaction_seq
    ):

        comm_line = {}
        comm_line["type"] = "communication"
        transaction_seq = transaction_seq + 1
        comm_line["sequence"] = transaction_seq
        comm_line["ref"] = line[2:10]
        comm_line["communication"] = comm_line["name"] = line[32:112].strip()
        coda_statement["coda_transactions"][transaction_seq] = comm_line

        return coda_parsing_note, transaction_seq

    def _coda_record_8(
        self, wiz_dict, coda_statement, line, coda_parsing_note, transaction_seq
    ):

        cba = coda_statement["coda_bank_params"]
        # get list of lines parsed already
        coda_transactions = coda_statement["coda_transactions"]

        if coda_transactions:
            last_transaction = coda_statement["main_move_stack"][-1]
            if last_transaction["type"] == "globalisation" and not last_transaction.get(
                "detail_cnt"
            ):
                # demote record with globalisation code from
                # 'globalisation' to 'regular' when no detail records
                main_transaction_seq = last_transaction["sequence"]
                to_demote = coda_transactions[main_transaction_seq]
                to_demote.update(
                    {
                        "type": "regular",
                        "glob_lvl_flag": 0,
                        "globalisation_amount": False,
                        "amount": last_transaction["globalisation_amount"],
                    }
                )
                # add closing globalisation level on previous detail record
                # in order to correctly close moves that have been 'promoted'
                # to globalisation
                if last_transaction.get("detail_cnt") and last_transaction.get(
                    "promoted"
                ):
                    closeglobalise = coda_transactions[transaction_seq - 1]
                    closeglobalise.update(
                        {"glob_lvl_flag": last_transaction["glob_lvl_flag"]}
                    )
        coda_statement["paper_nb_seq_number"] = line[1:4]
        bal_end = list2float(line[42:57])
        new_balance_date = str2date(line[57:63])
        if not new_balance_date:
            # take date of last transaction
            new_balance_date = last_transaction.get("entry_date")
        coda_statement["new_balance_date"] = new_balance_date
        if line[41] == "1":  # 1=Debit
            bal_end = -bal_end
        coda_statement["balance_end_real"] = bal_end

        # update coda_statement['name'] with data from 8 record
        coda_statement["name"] = cba.coda_st_naming % {
            "code": cba.journal_id.code or "",
            "year": coda_statement["new_balance_date"]
            and coda_statement["new_balance_date"][:4]
            or coda_statement["date"][:4],
            "y": coda_statement["new_balance_date"]
            and coda_statement["new_balance_date"][2:4]
            or coda_statement["date"][2:4],
            "coda": coda_statement["coda_seq_number"],
            "paper_ob": coda_statement["paper_ob_seq_number"],
            "paper": coda_statement["paper_nb_seq_number"],
        }
        # We have to skip the already processed statements
        # when we reprocess CODA file
        if wiz_dict["coda_id"]:
            old_statements = self.env["account.bank.statement"].search(
                [
                    ("coda_id", "=", wiz_dict["coda_id"]),
                    ("name", "=", coda_statement["name"]),
                ]
            )
            if old_statements:
                coda_statement["skip"] = True

        return coda_parsing_note

    def _coda_record_9(self, wiz_dict, coda_statement, line, coda_parsing_note):

        coda_statement["balance_min"] = list2float(line[22:37])
        coda_statement["balance_plus"] = list2float(line[37:52])
        if not coda_statement.get("balance_end_real"):
            coda_statement["balance_end_real"] = (
                coda_statement["balance_start"]
                + coda_statement["balance_plus"]
                - coda_statement["balance_min"]
            )
        if coda_parsing_note:
            coda_statement["coda_parsing_note"] = (
                _("'\nStatement Line matching results:") + coda_parsing_note
            )
        else:
            coda_statement["coda_parsing_note"] = ""

        return coda_parsing_note

    def _check_duplicate(self, wiz_dict, coda_statement):
        cba = coda_statement["coda_bank_params"]
        discard = False
        if cba.discard_dup:
            dups = self.env["account.bank.statement"].search(
                [
                    ("name", "=", coda_statement["name"]),
                    ("company_id", "=", cba.company_id.id),
                ]
            )
            if dups:
                # don't create a bank statement for duplicates
                discard = True
                wiz_dict["nb_err"] += 1
                wiz_dict["err_string"] += (
                    _(
                        "\nThe CODA processing tries to create Bank Statement %s, "
                        "but this statement already exists, "
                        "hence no duplicate Bank Statement has been created."
                    )
                    % coda_statement["name"]
                )
                if dups[0].coda_id:
                    wiz_dict["err_string"] += (
                        _("\nThis Bank Statement statement is linked to CODA FIle %s.")
                        % dups[0].coda_id.name
                    )
        return discard

    def _create_bank_statement(self, wiz_dict, coda_statement):

        bank_st = False
        cba = coda_statement["coda_bank_params"]
        journal = cba.journal_id
        balance_start_check = False
        balance_start_check_date = (
            coda_statement["first_transaction_date"] or coda_statement["date"]
        )
        st_check = self.env["account.bank.statement"].search(
            [("journal_id", "=", journal.id), ("date", "<", balance_start_check_date)],
            order="date DESC, id DESC",
            limit=1,
        )
        if st_check:
            balance_start_check = st_check.balance_end_real
        else:
            account = journal.default_account_id
            if not account:
                wiz_dict["nb_err"] += 1
                wiz_dict["err_string"] += (
                    _(
                        "'\nConfiguration Error in journal %s!"
                        "\nPlease verify the Default Debit and Credit Account "
                        "settings."
                    )
                    % journal.name
                )
                return bank_st
            else:
                data = self.env["account.move.line"].read_group(
                    [
                        ("account_id", "=", account.id),
                        ("date", "<", balance_start_check_date),
                    ],
                    ["balance"],
                    [],
                )
                balance_start_check = data and data[0]["balance"] or 0.0

        if not cba.currency_id.is_zero(
            balance_start_check - coda_statement["balance_start"]
        ):
            balance_start_err_string = _(
                "'\nThe CODA Statement %(name)s "
                "Starting Balance (%(balance_start).2f) "
                "does not correspond with the previous "
                "Closing Balance (%(balance_start_check).2f) in journal %(journal)s!"
            ) % {
                "name": coda_statement["name"],
                "balance_start": coda_statement["balance_start"],
                "balance_start_check": balance_start_check,
                "journal": journal.name,
            }
            if cba.balance_start_enforce:
                wiz_dict["nb_err"] += 1
                wiz_dict["err_string"] += balance_start_err_string
                return bank_st
            else:
                coda_statement["coda_parsing_note"] += "\n" + balance_start_err_string

        st_vals = {
            "name": coda_statement["name"],
            "journal_id": journal.id,
            "coda_id": wiz_dict["coda_id"],
            "date": coda_statement["new_balance_date"],
            "accounting_date": self.accounting_date,
            "balance_start": coda_statement["balance_start"],
            "balance_end_real": coda_statement["balance_end_real"],
            "state": "draft",
            "import_format": "coda",
            "company_id": cba.company_id.id,
            "coda_bank_account_id": cba.id,
        }

        try:
            st = self.env["account.bank.statement"].with_company(cba.company_id)
            bank_st = st.create(st_vals)
        except (UserError, ValidationError) as e:
            wiz_dict["nb_err"] += 1
            err_string = e.args[0]
            wiz_dict["err_string"] += _("\nApplication Error ! ") + err_string
            tb = "".join(format_exception(*exc_info()))
            _logger.error(
                "Application Error while processing Statement %s\n%s",
                coda_statement.get("name", "/"),
                tb,
            )
        except Exception as e:
            wiz_dict["nb_err"] += 1
            wiz_dict["err_string"] += _("\nSystem Error : ") + str(e)
            tb = "".join(format_exception(*exc_info()))
            _logger.error(
                "System Error while processing Statement %s\n%s",
                coda_statement.get("name", "/"),
                tb,
            )

        return bank_st

    def _prepare_statement_line(  # noqa: C901
        self, wiz_dict, coda_statement, transaction, coda_parsing_note
    ):

        cba = coda_statement["coda_bank_params"]

        if not transaction["type"] == "communication":
            if transaction["trans_family"] in ST_LINE_NAME_FAMILIES:
                transaction["name"] = self._get_st_line_name(wiz_dict, transaction)
            if transaction["type"] == "information":
                if transaction["struct_comm_type"] in PARSE_COMMS_INFO:
                    (
                        transaction["name"],
                        transaction["communication"],
                    ) = self._parse_comm_info(wiz_dict, coda_statement, transaction)
                elif transaction["struct_comm_type"] in PARSE_COMMS_MOVE:
                    (
                        transaction["name"],
                        transaction["communication"],
                    ) = self._parse_comm_move(wiz_dict, coda_statement, transaction)
            elif transaction["struct_comm_type"] in PARSE_COMMS_MOVE:
                transaction["struct_comm_raw"] = transaction["communication"]
                (
                    transaction["name"],
                    transaction["communication"],
                ) = self._parse_comm_move(wiz_dict, coda_statement, transaction)

        transaction["name"] = transaction["name"].strip()

        # handling transactional records, transaction['type'] in
        # ['globalisation', 'regular']

        if transaction["type"] in ["globalisation", "regular"]:

            if transaction["ref_move_detail"] == "0000":
                # initialise stack with tuples
                # (glob_lvl_flag, glob_code, glob_id, glob_name)
                coda_statement["glob_id_stack"] = [(0, "", 0, "")]

            glob_lvl_flag = transaction["glob_lvl_flag"]
            if glob_lvl_flag:
                if coda_statement["glob_id_stack"][-1][0] == glob_lvl_flag:
                    transaction["globalisation_id"] = coda_statement["glob_id_stack"][
                        -1
                    ][2]
                    coda_statement["glob_id_stack"].pop()
                else:
                    glob_name = transaction["name"].strip() or "/"
                    seq_mod = self.env["ir.sequence"].with_company(cba.company_id)
                    glob_code = seq_mod.next_by_code("statement.line.global")
                    glob_mod = self.env[
                        "account.bank.statement.line.global"
                    ].with_company(cba.company_id)
                    glob_line = glob_mod.create(
                        {
                            "code": glob_code,
                            "name": glob_name,
                            "type": "coda",
                            "parent_id": coda_statement["glob_id_stack"][-1][2],
                            "amount": transaction["globalisation_amount"],
                            "payment_reference": transaction["payment_reference"],
                            "currency_id": cba.currency_id.id,
                            "company_id": cba.company_id.id,
                        }
                    )
                    transaction["globalisation_id"] = glob_line.id
                    coda_statement["glob_id_stack"].append(
                        (glob_lvl_flag, glob_code, glob_line.id, glob_name)
                    )

            self._format_transaction_note(wiz_dict, coda_statement, transaction)

            if glob_lvl_flag == 0:
                transaction["globalisation_id"] = coda_statement["glob_id_stack"][-1][2]

            transaction["create_bank_st_line"] = True
            if transaction["amount"] != 0.0:
                if not transaction["name"]:
                    if transaction["globalisation_id"]:
                        transaction["name"] = (
                            coda_statement["glob_id_stack"][-1][3] or ""
                        )

        # handling non-transactional records:
        # transaction['type'] in ['information', 'communication']

        elif transaction["type"] == "information":

            transaction["globalisation_id"] = coda_statement["glob_id_stack"][-1][2]
            self._format_transaction_note(wiz_dict, coda_statement, transaction)
            # update transaction values generated from the
            # 2.x move record
            mm_seq = transaction["main_move_sequence"]
            coda_statement["coda_transactions"][mm_seq]["note"] += (
                INDENT8_HTML + transaction["communication"]
            )

        elif transaction["type"] == "communication":
            transaction["name"] = "free communication"
            coda_statement["coda_note"] += "\n" + transaction["communication"]

        if not transaction["name"]:
            transaction["name"] = ", ".join(
                [
                    transaction["trans_family_desc"],
                    transaction["trans_code_desc"],
                    transaction["trans_category_desc"],
                ]
            )
        return coda_parsing_note

    def _format_transaction_note(self, wiz_dict, coda_statement, transaction):
        if transaction["type"] == "information":
            transaction["note"] = _(
                "Transaction Type"
                ": %(trans_type)s - %(trans_type_desc)s"
                "\nTransaction Family: %(trans_family)s - %(trans_family_desc)s"
                "\nTransaction Code: %(trans_code)s - %(trans_code_desc)s"
                "\nTransaction Category: %(trans_category)s - %(trans_category_desc)s"
                "\nStructured Communication Type: "
                "%(struct_comm_type)s - %(struct_comm_type_desc)s"
                "\nCommunication: %(communication)s"
            ) % {
                "trans_type": transaction["trans_type"],
                "trans_type_desc": transaction["trans_type_desc"],
                "trans_family": transaction["trans_family"],
                "trans_family_desc": transaction["trans_family_desc"],
                "trans_code": transaction["trans_code"],
                "trans_code_desc": transaction["trans_code_desc"],
                "trans_category": transaction["trans_category"],
                "trans_category_desc": transaction["trans_category_desc"],
                "struct_comm_type": transaction["struct_comm_type"],
                "struct_comm_type_desc": transaction["struct_comm_type_desc"],
                "communication": transaction["communication"],
            }
        else:
            transaction["note"] = _(
                "Partner Name: %(partner_name)s "
                "\nPartner Account Number: %(counterparty_number)s"
                "\nTransaction Type: %(trans_type)s - %(trans_type_desc)s"
                "\nTransaction Family: %(trans_family)s - %(trans_family_desc)s"
                "\nTransaction Code: %(trans_code)s - %(trans_code_desc)s"
                "\nTransaction Category: %(trans_category)s - %(trans_category_desc)s"
                "\nStructured Communication Type: "
                "%(struct_comm_type)s - %(struct_comm_type_desc)s"
                "\nPayment Reference: %(payment_reference)s"
                "\nCommunication: %(communication)s"
            ) % {
                "partner_name": transaction["partner_name"],
                "counterparty_number": transaction["counterparty_number"],
                "trans_type": transaction["trans_type"],
                "trans_type_desc": transaction["trans_type_desc"],
                "trans_family": transaction["trans_family"],
                "trans_family_desc": transaction["trans_family_desc"],
                "trans_code": transaction["trans_code"],
                "trans_code_desc": transaction["trans_code_desc"],
                "trans_category": transaction["trans_category"],
                "trans_category_desc": transaction["trans_category_desc"],
                "struct_comm_type": transaction["struct_comm_type"],
                "struct_comm_type_desc": transaction["struct_comm_type_desc"],
                "payment_reference": transaction["payment_reference"],
                "communication": transaction["communication"],
            }

    def _get_st_line_move_name(self, wiz_dict, coda_statement, transaction):
        move_name = "{}/{}".format(
            coda_statement["name"], str(transaction["sequence"]).rjust(3, "0")
        )
        return move_name

    def _prepare_st_line_vals(self, wiz_dict, coda_statement, transaction):

        cba = coda_statement["coda_bank_params"]
        g_seq = transaction.get("glob_sequence")
        if g_seq:
            transaction["upper_transaction"] = coda_statement["coda_transactions"][
                g_seq
            ]
        move_name = self._get_st_line_move_name(wiz_dict, coda_statement, transaction)
        accounting_date = self.accounting_date or transaction["entry_date"]
        st_line_vals = {
            "sequence": transaction["sequence"],
            "ref": transaction["ref"],
            "payment_ref": transaction["name"],
            "transaction_date": transaction["entry_date"],
            "val_date": transaction["val_date"],
            "date": accounting_date,
            "amount": transaction["amount"],
            "partner_name": transaction["partner_name"],
            "counterparty_bic": transaction["counterparty_bic"],
            "counterparty_number": transaction["counterparty_number"],
            "counterparty_currency": transaction["counterparty_currency"],
            "globalisation_id": transaction["globalisation_id"],
            "payment_reference": transaction["payment_reference"],
            "statement_id": coda_statement["bank_st_id"],
            "name": move_name,
            "narration": transaction["note"].replace("\n", "<br>"),
            "coda_transaction_dict": json.dumps(transaction),
        }

        if transaction["type"] == "globalisation":
            st_line_vals["transaction_type"] = "globalisation"

        if transaction.get("bank_account_id"):
            st_line_vals["bank_account_id"] = transaction["bank_account_id"]

        if (
            coda_statement["currency"] != "EUR"
            and cba.company_id.currency_id.name == "EUR"
            and transaction["struct_comm_type"] == "105"
            and transaction.get("struct_comm_details")
        ):
            amount_eur = transaction["struct_comm_details"].get("amount_eur")
            if amount_eur and transaction["type"] == "regular":
                st_line_vals.update(
                    {
                        "foreign_currency_id": cba.company_id.currency_id.id,
                        "amount_currency": amount_eur,
                    }
                )

        return st_line_vals

    def _create_bank_statement_line(self, wiz_dict, coda_statement, transaction):
        st_line_vals = self._prepare_st_line_vals(wiz_dict, coda_statement, transaction)
        cba = coda_statement["coda_bank_params"]
        stl = self.env["account.bank.statement.line"].with_company(cba.company_id)
        st_line = stl.create(st_line_vals)
        transaction["st_line_id"] = st_line.id

    def _discard_empty_statement(self, wiz_dict, coda_statement):
        """
        Return False if you do not want to create a bank statement
        for CODA files without transactions.
        """
        coda_statement["coda_parsing_note"] += _(
            "\n\nThe CODA Statement %(name)s does not contain transactions, "
            "hence no Bank Statement has been created."
            "\nSelect the 'CODA Bank Statement' "
            "to check the contents of %(name)s."
        ) % {"name": coda_statement["name"]}
        return True

    def _coda_statement_init_hook(self, wiz_dict, coda_statement):
        """
        Use this method to take customer specific actions
        once a specific statement has been identified in a coda file.
        """

    def _coda_statement_hook(self, wiz_dict, coda_statement):
        """
        Use this method to take customer specific actions
        after the creation of the 'coda_statement' dict by the parsing engine.

        e.g. Do not generate statements without transactions:
        self._normal2info(wiz_dict, coda_statement)
        """

    def _coda_transaction_hook(self, wiz_dict, coda_statement, transaction):
        """
        Use this method to adapt the transaction created by the
        CODA parsing to customer specific needs.
        This hook is also used by the l10n_be_coda_card cost module.
        """
        transaction_copy = transaction.copy()
        return [transaction_copy]

    def coda_import(self):
        self = self.with_context(allowed_company_ids=self.env.user.company_ids.ids)
        import_results = []
        wiz_dict = {
            "ziperr_log": "",
        }
        if self.coda_fname.split(".")[-1].lower() == "zip":
            coda_files = self._coda_zip(wiz_dict)
        else:
            coda_files = [(None, base64.decodebytes(self.coda_data), self.coda_fname)]

        for coda_file in coda_files:
            try:
                with self.env.cr.savepoint():
                    coda, statements, note = self._coda_parsing(
                        wiz_dict, codafile=coda_file[1], codafilename=coda_file[2]
                    )
                    import_results += [(coda, statements, note)]
            except (UserError, ValidationError) as e:
                err_string = _(
                    "\n\nError while processing CODA File '%(fn)s' :\n%(err_msg)s"
                ) % {
                    "fn": coda_file[2],
                    "err_msg": "".join(e.args),
                }
                import_results += [
                    (
                        self.env["account.coda"],
                        self.env["account.bank.statement"],
                        err_string,
                    )
                ]
            except Exception:
                tb = "".join(format_exception(*exc_info()))
                err_string = _(
                    "\n\nError while processing CODA File '%(fn)s' :\n%(tb)s"
                ) % {
                    "fn": coda_file[2],
                    "tb": tb,
                }
                import_results += [
                    (
                        self.env["account.coda"],
                        self.env["account.bank.statement"],
                        err_string,
                    )
                ]

        coda_files = self.env["account.coda"]
        bank_statements = self.env["account.bank.statement"]
        for entry in import_results:
            coda_files |= entry[0]
            bank_statements |= entry[1]

        wiz_note = "\n\n".join([x[2] for x in import_results])
        if self.reconcile:
            wiz_note = ""
            for i, entry in enumerate(import_results):
                if i:
                    wiz_note += "\n\n"
                coda = entry[0]
                statements = entry[1]
                wiz_note += entry[2]
                time_start = time.time()
                for statement in statements:
                    self = self.with_company(statement.company_id)
                    statement = statement.with_company(statement.company_id)
                    reconcile_note = self._automatic_reconcile(wiz_dict, statement)
                    if reconcile_note:
                        wiz_note += "\n\n"
                        wiz_note += _("Automatic Reconcile remarks:") + reconcile_note
                if statements:
                    wiz_note += "\n\n"
                    wiz_note += (
                        _("Number of statements reconciled")
                        + " : "
                        + str(len(statements))
                    )
                processing_time = time.time() - time_start
                _logger.warning(
                    "File %s processing time = %.3f seconds", coda.name, processing_time
                )

        wiz_note = wiz_dict["ziperr_log"] + wiz_note
        self.note = wiz_note
        ctx = dict(
            self.env.context,
            coda_ids=coda_files.ids,
            bank_statement_ids=bank_statements.ids,
        )
        module = __name__.split("addons.")[1].split(".")[0]
        result_view = self.env.ref("%s.account_coda_import_view_form_result" % module)
        return {
            "name": _("Import CODA File result"),
            "res_id": self.id,
            "view_type": "form",
            "view_mode": "form",
            "res_model": "account.coda.import",
            "view_id": result_view.id,
            "target": "new",
            "context": ctx,
            "type": "ir.actions.act_window",
        }

    def _coda_zip(self, wiz_dict):
        """
        Expand ZIP archive before CODA parsing.
        """
        coda_files = []
        try:
            coda_data = base64.decodebytes(self.coda_data)
            with zipfile.ZipFile(BytesIO(coda_data)) as coda_zip:
                for fn in coda_zip.namelist():
                    if fn.endswith("/") or fn.startswith("__MACOSX/"):
                        continue
                    coda_files.append((coda_zip.read(fn), fn))
        # fall back to regular CODA file processing if zip expand fails
        except zipfile.BadZipfile as e:
            _logger.error(str(e))
            return self._coda_parsing(wiz_dict)
        except Exception:
            tb = "".join(format_exception(*exc_info()))
            _logger.error("Unknown Error while reading zip file\n%s", tb)
            return self._coda_parsing(wiz_dict)
        coda_files = self._sort_files(wiz_dict, coda_files)
        return coda_files

    def _msg_duplicate(self, wiz_dict, filename):
        wiz_dict["nb_err"] += 1
        wiz_dict["ziperr_log"] += _("\n\nError while processing CODA File '%s' :") % (
            filename
        )
        wiz_dict["ziperr_log"] += _(
            "\nThis CODA File is marked by your bank as a 'Duplicate' !"
        )
        wiz_dict["ziperr_log"] += _("\nPlease treat this CODA File manually !")

    def _msg_exception(self, wiz_dict, filename):
        wiz_dict["nb_err"] += 1
        wiz_dict["ziperr_log"] += _("\n\nError while processing CODA File '%s' :") % (
            filename
        )
        wiz_dict["ziperr_log"] += _("\nInvalid Header Record !")

    def _msg_noheader(self, wiz_dict, filename):
        wiz_dict["nb_err"] += 1
        wiz_dict["ziperr_log"] += _("\n\nError while processing CODA File '%s' :") % (
            filename
        )
        wiz_dict["ziperr_log"] += _("\nMissing Header Record !")

    def _sort_files(self, wiz_dict, coda_files_in):
        """
        Sort CODA files on creation date.
        """
        coda_files = []
        for data, filename in coda_files_in:
            coda_creation_date = False
            recordlist = str(data, "windows-1252", "strict").split("\n")
            if not recordlist:
                wiz_dict["nb_err"] += 1
                wiz_dict["ziperr_log"] += _(
                    "\n\nError while processing CODA File '%s' :"
                ) % (filename)
                wiz_dict["ziperr_log"] += _("\nEmpty File !")
            else:
                for line in recordlist:
                    if not line:
                        pass
                    elif line[0] == "0":
                        try:
                            coda_creation_date = str2date(line[5:11])
                            if line[16] == "D":
                                self._msg_duplicate(wiz_dict, filename)
                            else:
                                coda_files += [(coda_creation_date, data, filename)]
                        except Exception:
                            self._msg_exception(wiz_dict, filename)
                        break
                    else:
                        self._msg_noheader(wiz_dict, filename)
                        break
        coda_files.sort()
        return coda_files

    def _coda_parsing(self, wiz_dict, codafile, codafilename):  # noqa: C901
        wiz_dict.update(
            {
                "nb_err": 0,
                "err_string": "",
                "coda_id": self.env.context.get("coda_id"),
                "coda_banks": self.env["coda.bank.account"]
                .sudo()
                .search([("company_id", "in", self.env.user.company_ids.ids)]),
                "trans_types": self.env["account.coda.trans.type"].search([]),
                "trans_codes": self.env["account.coda.trans.code"].search([]),
                "trans_categs": self.env["account.coda.trans.category"].search([]),
                "comm_types": self.env["account.coda.comm.type"].search([]),
                "coda_import_note": "",
            }
        )
        note = ""
        recordlist = str(codafile, "windows-1252", "strict").split("\n")
        coda_statements = []
        coda = self.env["account.coda"]

        # parse lines in coda file and store result in coda_statements list
        coda_statement = {}
        skip = False
        for line in recordlist:

            skip = coda_statement.get("skip")
            if not line:
                continue
            if line[0] != "0" and not coda_statement:
                raise UserError(
                    _("CODA Import Failed." "\nIncorrect input file format")
                )
            elif line[0] == "0":
                # start of a new statement within the CODA file
                coda_statement = {}
                st_line_seq = 0
                coda_parsing_note = ""

                coda_parsing_note = self._coda_record_0(
                    wiz_dict, coda_statement, line, coda_parsing_note
                )

                if not wiz_dict["coda_id"]:
                    coda = self.env["account.coda"].search(
                        [
                            ("name", "=", codafilename),
                            ("coda_creation_date", "=", coda_statement["date"]),
                        ],
                        limit=1,
                    )
                    wiz_dict["coda_id"] = coda.id
                    if wiz_dict["coda_id"]:
                        wiz_dict["coda_import_note"] += "\n\n"
                        wiz_dict["coda_import_note"] += (
                            _("CODA File %s has already been imported.") % codafilename
                        )
                else:
                    coda = self.env["account.coda"].browse(wiz_dict["coda_id"])

            elif line[0] == "1":
                coda_parsing_note = self._coda_record_1(
                    wiz_dict, coda_statement, line, coda_parsing_note
                )

            elif line[0] == "2" and not skip:
                # movement data record 2
                coda_parsing_note, st_line_seq = self._coda_record_2(
                    wiz_dict, coda_statement, line, coda_parsing_note, st_line_seq
                )

            elif line[0] == "3" and not skip:
                # information data record 3
                coda_parsing_note, st_line_seq = self._coda_record_3(
                    wiz_dict, coda_statement, line, coda_parsing_note, st_line_seq
                )

            elif line[0] == "4" and not skip:
                # free communication data record 4
                coda_parsing_note, st_line_seq = self._coda_record_4(
                    wiz_dict, coda_statement, line, coda_parsing_note, st_line_seq
                )

            elif line[0] == "8" and not skip:
                # new balance record
                coda_parsing_note = self._coda_record_8(
                    wiz_dict, coda_statement, line, coda_parsing_note, st_line_seq
                )

            elif line[0] == "9":
                # footer record
                coda_parsing_note = self._coda_record_9(
                    wiz_dict, coda_statement, line, coda_parsing_note
                )
                if not coda_statement["skip"]:
                    coda_statements.append(coda_statement)

        # end for line in recordlist:

        if not wiz_dict["coda_id"]:
            err_string = ""
            try:
                coda = self.env["account.coda"].create(
                    {
                        "name": codafilename,
                        "coda_data": base64.b64encode(codafile),
                        "coda_creation_date": coda_statement["date"],
                        "date": fields.Date.context_today(self),
                        "user_id": self.env.uid,
                    }
                )
                wiz_dict["coda_id"] = coda.id
            except (UserError, ValidationError) as e:
                err_string = e.args[0]
                err_string = _("\nApplication Error : ") + err_string
            except Exception as e:
                err_string = _("\nSystem Error : ") + str(e)
            if err_string:
                raise UserError(_("CODA Import failed !") + err_string)

        bank_statements = self.env["account.bank.statement"]

        for coda_statement in coda_statements:

            bank_st = False
            cba = coda_statement["coda_bank_params"]
            self._coda_statement_hook(wiz_dict, coda_statement)
            discard = self._check_duplicate(wiz_dict, coda_statement)
            transactions = coda_statement["coda_transactions"]

            if not transactions:
                err_string = _(
                    "\nThe CODA File contains empty CODA Statement %(seq)s "
                    "for Bank Account %(bank)s !"
                ) % {
                    "seq": coda_statement["coda_seq_number"],
                    "bank": coda_statement["acc_number"]
                    + " ("
                    + coda_statement["currency"]
                    + ") - "
                    + coda_statement["description"],
                }
                wiz_dict["coda_import_note"] += "\n" + err_string
                discard = self._discard_empty_statement(wiz_dict, coda_statement)

            if not discard and not coda_statement.get("skip"):
                bank_st = self._create_bank_statement(wiz_dict, coda_statement)
                if bank_st:
                    bank_statements += bank_st
                    coda_statement["bank_st_id"] = bank_st.id
                    coda.company_ids |= coda_statement["coda_bank_params"].company_id
                else:
                    break
            else:
                break

            # prepare bank statement line values and merge
            # information records into the statement line
            coda_statement["glob_id_stack"] = []

            coda_parsing_note = coda_statement["coda_parsing_note"]

            for x in transactions:
                transaction = transactions[x]
                coda_parsing_note = self._prepare_statement_line(
                    wiz_dict, coda_statement, transaction, coda_parsing_note
                )

            bank_st_transactions = []
            for x in transactions:
                transaction = transactions[x]
                if transaction.get("create_bank_st_line"):
                    res_transaction_hook = self._coda_transaction_hook(
                        wiz_dict, coda_statement, transaction
                    )
                    if res_transaction_hook:
                        bank_st_transactions += res_transaction_hook

            # resequence since _coda_transaction_hook may add/remove lines
            transaction_seq = 0
            st_balance_end = round(coda_statement["balance_start"], 2)
            for transaction in bank_st_transactions:
                transaction_seq += 1
                transaction["sequence"] = transaction_seq
                st_balance_end += round(transaction["amount"], 2)
                self._create_bank_statement_line(wiz_dict, coda_statement, transaction)

            if round(st_balance_end - coda_statement["balance_end_real"], 2):
                err_string = _(
                    "\nIncorrect ending Balance in CODA Statement %(seq)s "
                    "for Bank Account %(bank)s !"
                ) % {
                    "seq": coda_statement["coda_seq_number"],
                    "bank": coda_statement["acc_number"]
                    + " ("
                    + coda_statement["currency"]
                    + ") - "
                    + coda_statement["description"],
                }
                coda_statement["coda_parsing_note"] += "\n" + err_string

            # trigger calculate balance_end
            bank_st.write({"balance_start": coda_statement["balance_start"]})
            journal_name = cba.journal_id.name

            coda_statement["coda_parsing_note"] = coda_parsing_note

            wiz_dict["coda_import_note"] += _(
                "\n\nBank Journal: %(journal_name)s"
                "\nCODA Version: %(coda_version)s"
                "\nCODA Sequence Number: %(coda_seq_number)s"
                "\nPaper Statement Sequence Number: %(paper_nb_seq_number)s"
                "\nBank Account: %(bank)s"
                "\nAccount Holder Name: %(acc_holder)s"
                "\nDate: %(date)s, Starting Balance:  %(balance_start).2f, "
                "Ending Balance: %(balance_end_real).2f"
                "%(coda_parsing_note)s"
            ) % {
                "journal_name": journal_name,
                "coda_version": coda_statement["coda_version"],
                "coda_seq_number": coda_statement["coda_seq_number"],
                "paper_nb_seq_number": coda_statement.get("paper_nb_seq_number")
                or coda_statement["paper_ob_seq_number"],
                "bank": coda_statement["acc_number"]
                + " ("
                + coda_statement["currency"]
                + ") - "
                + coda_statement["description"],
                "acc_holder": coda_statement["acc_holder"],
                "date": coda_statement["date"],
                "balance_start": float(coda_statement["balance_start"]),
                "balance_end_real": float(coda_statement["balance_end_real"]),
                "coda_parsing_note": coda_statement["coda_parsing_note"],
            }

            if coda_statement.get("separate_application") != "00000":
                wiz_dict["coda_import_note"] += (
                    _("'\nCode Separate Application: %s")
                    % coda_statement["separate_application"]
                )
            if coda_statement["coda_note"]:
                bank_st.write({"coda_note": coda_statement["coda_note"]})

        # end 'for coda_statement in coda_statements'

        coda_note_header = ">>> " + time.strftime("%Y-%m-%d %H:%M:%S") + " "
        coda_note_header += _("The CODA File has been processed by")
        coda_note_header += " %s :" % self.env.user.name
        coda_note_footer = (
            "\n\n"
            + _("Number of statements parsed")
            + " : "
            + str(len(coda_statements))
        )

        if not wiz_dict["nb_err"]:
            coda = self.env["account.coda"].browse(wiz_dict["coda_id"])
            old_note = coda.note and (coda.note + "\n\n") or ""
            note = coda_note_header + wiz_dict["coda_import_note"] + coda_note_footer
            coda.write({"note": old_note + note, "state": "done"})
        else:
            note = (
                _("Errors detected during the processing of " "CODA File %s :")
                % codafilename
            )
            note += "\n" + wiz_dict["err_string"]

        return coda, bank_statements, note

    def _automatic_reconcile(
        self, wiz_dict, statement, reconcile_note="", st_lines=None
    ):
        """
        Large statements may result in a MemoryError.
        The memory usage goes exponential at some point in time.
        As a workaround we commit every transaction so that the
        reconcilation process can be completed via the 'Automatic Reconcile'
        button on the bank statement or bank_statement_line.
        """
        reconcile_note = reconcile_note or ""
        self.accounting_date = statement.accounting_date
        cba = statement.coda_bank_account_id
        if not cba:
            return reconcile_note
        lines = statement.line_ids.filtered(
            lambda r: r.amount and r.coda_transaction_dict and not r.is_reconciled
        )
        if st_lines:
            lines = lines.filtered(lambda r: r in st_lines)
        config_param = self.env["ir.config_parameter"].sudo()
        size = config_param.get_param("coda.reconcile.transaction.thread.size", 50)
        splitted_lines = tools.split_every(int(size), lines)

        for st_lines in splitted_lines:
            reconcile_note, error = self._st_line_reconcile_thread(
                wiz_dict, st_lines, reconcile_note
            )
            if error:
                break

        return reconcile_note

    def _st_line_reconcile_thread(self, wiz_dict, st_lines, reconcile_note):
        error = False
        cba = st_lines[0].statement_id.coda_bank_account_id
        wiz_dict["company_bank_accounts"] = cba.company_id.bank_journal_ids.mapped(
            "bank_account_id"
        ).mapped("sanitized_acc_number")

        for st_line in st_lines:
            transaction = st_line.coda_transaction_dict and json.loads(
                st_line.coda_transaction_dict
            )
            try:
                with self.env.cr.savepoint():
                    reconcile_note += self._st_line_reconcile(
                        wiz_dict, st_line, cba, transaction, reconcile_note
                    )
            except MemoryError:
                err_msg = (
                    "MemoryError while processing statement line " "with ref '%s'"
                ) % transaction["ref"]
                _logger.error(err_msg)
                error = "MemoryError"
                # replace reconcile note with MemoryError message
                line_notes = [error]
                line_notes.append(
                    "Use the 'AUTOMATIC RECONCILE' button in the "
                    "bank statement to complete the "
                    "reconciliation process"
                )
                reconcile_note = self._format_line_notes(
                    wiz_dict, st_line, cba, transaction, line_notes, force=True
                )
                break
            except (UserError, ValidationError) as e:
                line_note = _("Application Error : ") + e.args[0]
                reconcile_note += self._format_line_notes(
                    wiz_dict, st_line, cba, transaction, [line_note], force=True
                )
            except Exception as e:
                line_note = _("System Error : ") + str(e)
                reconcile_note += self._format_line_notes(
                    wiz_dict, st_line, cba, transaction, [line_note], force=True
                )
                exctype, value = exc_info()[:2]
                log_err = "{}: {}".format(exctype.__name__, str(value))
                log_err = self._format_line_notes(
                    wiz_dict, st_line, cba, transaction, [log_err], force=True
                )
                _logger.error(log_err)

        config_param = self.env["ir.config_parameter"].sudo()
        note_size = int(config_param.get_param("coda.reconcile.note.size", 10000))
        if note_size < len(reconcile_note):
            reconcile_note = reconcile_note[:note_size]
            msg = "Reconcile notes have been truncated"
            reconcile_note += "\n" + 10 * "=" + " " + msg + " " + 10 * "="
        return reconcile_note, error

    def _st_line_reconcile(self, wiz_dict, st_line, cba, transaction, reconcile_note):
        transaction["matching_info"] = {"status": "ongoing"}
        match_info = transaction["matching_info"]
        reconcile_note = self._match_and_reconcile(
            wiz_dict, st_line, cba, transaction, reconcile_note
        )
        if match_info["status"] == "break":
            return reconcile_note
        if cba.update_partner:
            reconcile_note = self._update_partner_bank(
                wiz_dict, st_line, cba, transaction, reconcile_note
            )

        # override default account mapping by mappings
        # defined in rules engine
        if not match_info.get("counterpart_amls") or match_info.get("account_id"):
            if cba.account_mapping_ids:
                rule = self.env["coda.account.mapping.rule"]._rule_get(
                    transaction, st_line, cba
                )
                if rule:
                    for k in rule:
                        match_info[k] = rule[k]

        if (
            match_info.get("partner_id")
            and st_line.partner_id.id != match_info["partner_id"]
        ):
            st_line.write({"partner_id": match_info["partner_id"]})

        if match_info.get("counterpart_amls") or match_info.get("account_id"):
            reconcile_note = self._create_move_and_reconcile(
                wiz_dict, st_line, cba, transaction, reconcile_note
            )

        return reconcile_note

    def _match_and_reconcile(self, wiz_dict, st_line, cba, transaction, reconcile_note):
        """
        Matching and Reconciliation logic.
        During the processing, the different steps can add
        info to the transaction['matching_info'] dict.

        Setting transaction['matching_info']{'status'] to 'done' will stop
        the matching processing.

        Setting transaction['matching_info']{'status'] to 'break' will also
        stop the 'post-matching' processing such as
        - update partner_id
        - update partner bank account
        - rules engine

        Returns: reconcile_note
        """
        match_status = transaction["matching_info"]["status"]

        # Customer specific logic may have taken this method in inherit
        # and done the matching
        if match_status in ["break", "done"]:
            return reconcile_note

        # match on payment reference
        if cba.has_payment_module and cba.find_payment:
            reconcile_note = self._match_pain_reference(
                wiz_dict, st_line, cba, transaction, reconcile_note
            )
            if match_status in ["break", "done"]:
                return reconcile_note

        # match on invoice
        reconcile_note = self._match_invoice(
            wiz_dict, st_line, cba, transaction, reconcile_note
        )
        if match_status in ["break", "done"]:
            return reconcile_note

        # match on sale order
        if cba.has_sale_module and cba.find_so_number:
            reconcile_note = self._match_sale_order(
                wiz_dict, st_line, cba, transaction, reconcile_note
            )
            if match_status in ["break", "done"]:
                return reconcile_note

        # match on open accounting entries
        if cba.find_account_move_line:
            reconcile_note = self._match_account_move_line(
                wiz_dict, st_line, cba, transaction, reconcile_note
            )
            if match_status in ["break", "done"]:
                return reconcile_note

        # check if internal_transfer or find partner via counterparty_number
        # when previous lookup steps fail
        reconcile_note = self._match_counterparty(
            wiz_dict, st_line, cba, transaction, reconcile_note
        )
        if match_status in ["break", "done"]:
            return reconcile_note

        return reconcile_note

    def _match_pain_reference(
        self, wiz_dict, st_line, cba, transaction, reconcile_note
    ):
        """
        Check payment reference in bank transaction against payment order entries.
        """
        match_info = transaction["matching_info"]

        if self._skip_payment_reference_match(
            wiz_dict, st_line, cba, transaction, reconcile_note
        ):
            return reconcile_note

        payment = self.env["account.payment"]
        if "account.payment.order" in self.env:
            payment = self._match_pain_reference_oca(
                wiz_dict, st_line, cba, transaction, reconcile_note
            )
        if not payment and "account.batch.payment" in self.env:
            payment = self._match_pain_reference_oe(
                wiz_dict, st_line, cba, transaction, reconcile_note
            )

        if not payment:
            return reconcile_note
        aml = payment.move_id.line_ids.filtered(
            lambda r: r.account_id == payment.outstanding_account_id
        )
        match_info["counterpart_amls"] = [(aml, aml.balance)]
        match_info["status"] = "done"
        match_info["partner_id"] = aml.partner_id.id
        return reconcile_note

    def _match_pain_reference_oca(
        self, wiz_dict, st_line, cba, transaction, reconcile_note
    ):
        """
        Check payment reference in bank transaction against account.payment.order
        entries.
        """
        e2e = transaction["payment_reference"]
        e2e_id = e2e.isdigit() and int(e2e)
        if not e2e_id:
            # SCT pain files generated by OCA module have always
            # an integer EndToEndId
            return self.env["account.payment"]
        return self.env["account.payment"].search([("move_id", "=", e2e_id)])

    def _match_pain_reference_oe(
        self, wiz_dict, st_line, cba, transaction, reconcile_note
    ):
        """
        ISO 20022 Payment Order matching when using Odoo Enterprise
        account_batch_payment (account_sepa)

        The Odoo Enterprise account_sepa module doesn't provide a straigthforward
        way to match the pain <EndToEndId> with account.payment record in
        Odoo hence we need to use some crippled logic to do so.

        The <EndToEndId> is created as follows:

          val_MsgId = str(time.time())
          PmtInfId.text = (val_MsgId + str(self.id) + str(count))[-30:]
          EndToEndId.text = (PmtInfId.text + str(payment['id']))[-30:].strip()

        TODO: extend logic for SEPA Direct Debit
        """
        amt_paid = transaction["amount"]
        e2e = transaction["payment_reference"]
        payments = self.env["account.payment"].search(
            [
                ("payment_type", "=", "outbound"),
                ("amount", "=", -amt_paid),
                ("payment_method_id.code", "=", "sepa_ct"),
                ("state", "=", "posted"),
                (
                    "partner_bank_id.sanitized_acc_number",
                    "=",
                    transaction["counterparty_number"],
                ),
            ]
        )
        payment = payments.filtered(lambda r: e2e.endswith(str(r.id)))
        if payment:
            # double-check payment communication
            if payment.ref not in (
                transaction["struct_comm_bba"],
                transaction["communication"],
            ):
                return self.env["account.payment"]

        return payment

    def _skip_payment_reference_match(
        self, wiz_dict, st_line, cba, transaction, reconcile_note
    ):
        skip = False
        if not transaction["payment_reference"]:
            skip = True
        if transaction["amount"] >= 0.0:
            skip = True

        matching_key = False
        for k in TRANSACTION_KEYS:
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

    def _match_sale_order(self, wiz_dict, st_line, cba, transaction, reconcile_note):
        match_info = transaction["matching_info"]

        if match_info["status"] in ["break", "done"]:
            return reconcile_note

        if transaction["communication"] and transaction["amount"] > 0:
            reconcile_note, so_res = self._get_sale_order(
                wiz_dict, st_line, cba, transaction, reconcile_note
            )
            if so_res and len(so_res) == 1:
                so_id = so_res[0][0]
                match_info["status"] = "done"
                match_info["sale_order_id"] = so_id
                sale_order = self.env["sale.order"].browse(so_id)
                partner = sale_order.partner_id.commercial_partner_id
                match_info["partner_id"] = partner.id
                reconcile_note = self._so_invoice_amount_match(
                    wiz_dict, sale_order.invoice_ids, cba, transaction, reconcile_note
                )

        return reconcile_note

    def _get_sale_order(self, wiz_dict, st_line, cba, transaction, reconcile_note):
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

    def _so_invoice_amount_match(
        self, wiz_dict, invoices, cba, transaction, reconcile_note
    ):
        if not invoices:
            return reconcile_note

        if invoices.mapped("currency_id") != cba.currency_id:
            return reconcile_note

        cur = cba.currency_id
        amls = invoices.mapped("line_ids").filtered(
            lambda r: r.account_type == "asset_receivable"
            and r.parent_state == "posted"
            and not r.reconciled
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

    def _match_invoice_payment_reference(
        self, wiz_dict, st_Line, cba, transaction, reconcile_note, free_comm
    ):
        """
        check matching invoice number in free form communication
        combined with matching amount
        """
        inv_ids = False
        amount_fmt = "%.2f"
        if transaction["amount"] > 0:
            amount_rounded = amount_fmt % round(transaction["amount"], 2)
        else:
            amount_rounded = amount_fmt % round(-transaction["amount"], 2)

        select = """
            SELECT id FROM account_move
              WHERE payment_state != 'paid'
                AND company_id = {cpy_id}
                AND state = 'posted'
                AND round(amount_total, 2) = {amount}
        """.format(
            cpy_id=cba.company_id.id,
            amount=amount_rounded,
        )

        # 'out_invoice', 'in_refund'
        if transaction["amount"] > 0:
            select2 = """
                AND move_type = 'out_invoice'
                AND POSITION(name IN '{free_comm}') > 0
            """.format(
                free_comm=free_comm
            )
            self.env.cr.execute(select + select2)  # pylint: disable=E8103
            res = self.env.cr.fetchall()
            if res:
                inv_ids = [x[0] for x in res]
            else:
                select2 = """
                    AND move_type = 'in_refund'
                    AND (
                      (
                        COALESCE(payment_reference, '') != ''
                        AND POSITION(payment_reference IN '{free_comm}') > 0
                      ) OR (
                        COALESCE(ref, '') != ''
                        AND POSITION(ref IN '{free_comm}') > 0
                      )
                    )
                """.format(
                    free_comm=free_comm
                )
                self.env.cr.execute(select + select2)  # pylint: disable=E8103
                res = self.env.cr.fetchall()
                if res:
                    inv_ids = [x[0] for x in res]

        # 'in_invoice', 'out_refund'
        else:
            select2 = """
                AND move_type = 'in_invoice'
                AND (
                  (
                    COALESCE(payment_reference, '') != ''
                    AND POSITION(payment_reference IN '{free_comm}') > 0
                  ) OR (
                    COALESCE(ref, '') != ''
                    AND POSITION(ref IN '{free_comm}') > 0
                  )
                )
            """.format(
                free_comm=free_comm
            )
            self.env.cr.execute(select + select2)  # pylint: disable=E8103
            res = self.env.cr.fetchall()
            if res:
                inv_ids = [x[0] for x in res]
            else:
                select2 = """
                    AND move_type = 'out_refund'
                    AND POSITION(name IN '{free_comm}') > 0
                """.format(
                    free_comm=free_comm
                )
                self.env.cr.execute(select + select2)  # pylint: disable=E8103
                res = self.env.cr.fetchall()
                if res:
                    inv_ids = [x[0] for x in res]

        return inv_ids

    def _match_invoice(  # noqa: C901
        self, wiz_dict, st_line, cba, transaction, reconcile_note
    ):
        match_info = transaction["matching_info"]
        if match_info["status"] in ["break", "done"]:
            return reconcile_note

        # check bba scor in bank statement line against open invoices
        if transaction["struct_comm_bba"] and cba.find_bbacom:
            if transaction["amount"] > 0:
                domain = [("move_type", "in", ["out_invoice", "in_refund"])]
            else:
                domain = [("move_type", "in", ["in_invoice", "out_refund"])]
            domain += [
                ("state", "=", "posted"),
                ("payment_state", "!=", "paid"),
                ("payment_reference", "=", transaction["struct_comm_bba"]),
                ("company_id", "=", cba.company_id.id),
            ]
            invoices = self.env["account.move"].search(domain)
            if not invoices:
                line_note = _(
                    "There is no invoice matching the "
                    "Structured Communication '%s' !"
                ) % (transaction["struct_comm_bba"])
                reconcile_note += self._format_line_notes(
                    wiz_dict, st_line, cba, transaction, [line_note]
                )
            elif len(invoices) == 1:
                match_info["invoice_id"] = invoices[0].id
            elif len(invoices) > 1:
                line_notes = [
                    _(
                        "There is no invoice matching the "
                        "Structured Communication '%s' !"
                    )
                    % (transaction["struct_comm_bba"])
                ]
                line_notes.append(_("A manual reconciliation is required."))
                reconcile_note += self._format_line_notes(
                    wiz_dict, st_line, cba, transaction, line_notes
                )
        # use free comm in bank statement line
        # for lookup against open invoices
        if not match_info.get("invoice_id") and cba.find_bbacom:
            # Extract possible bba scor from free form communication
            # and try to find matching invoice.
            # We also match in this case on amount to mimimise risk on
            # false positives.
            free_comm_digits = re.sub(r"\D", "", transaction["communication"] or "")
            if len(free_comm_digits) >= 12:
                amount_fmt = "%.2f"
                if transaction["amount"] > 0:
                    amount_rounded = amount_fmt % round(transaction["amount"], 2)
                else:
                    amount_rounded = amount_fmt % round(-transaction["amount"], 2)
                select = r"""
    SELECT id FROM (
      SELECT id, move_type, state, amount_total, name,
      REGEXP_REPLACE(payment_reference, '[^0-9]', '', 'g') AS payref_normalised,
      '{}'::text AS free_comm_digits
        FROM account_move
        WHERE payment_state != 'paid' AND state = 'posted'
          AND company_id = {}
          AND ROUND(amount_total, 2) = {}
      ) sq
      WHERE LENGTH(payref_normalised) = 12
        AND free_comm_digits LIKE '%'||payref_normalised||'%'
                """.format(
                    free_comm_digits,
                    cba.company_id.id,
                    amount_rounded,
                )
                if transaction["amount"] > 0:
                    select2 = " AND move_type IN ('out_invoice', 'in_refund')"
                else:
                    select2 = " AND move_type IN ('in_invoice', 'out_refund')"
                self.env.cr.execute(select + select2)  # pylint: disable=E8103
                res = self.env.cr.fetchall()
                if res:
                    inv_ids = [x[0] for x in res]
                    if len(inv_ids) == 1:
                        match_info["invoice_id"] = inv_ids[0]

        if (
            not match_info.get("invoice_id")
            and cba.find_inv_number
            and (transaction["communication"] or transaction["payment_reference"])
        ):
            inv_ids = False

            # check matching invoice number in free form communication
            free_comm = repl_special(transaction["communication"].strip())
            # We do remark that the payment communication ends up sometimes in
            # the payment reference field in case of transactions from foreign
            # bank accounts.
            if (
                not free_comm
                and transaction["counterparty_number"]
                and transaction["counterparty_number"][:2] != "BE"
            ):
                free_comm = repl_special(transaction["payment_reference"].strip())
            if free_comm:
                inv_ids = self._match_invoice_payment_reference(
                    wiz_dict, st_line, cba, transaction, reconcile_note, free_comm
                )
            if not inv_ids:
                # check matching invoice number in free form communication
                # of upper globalisation level line
                if transaction.get("upper_transaction"):
                    free_comm = repl_special(
                        transaction["upper_transaction"]["communication"].strip()
                    )
                    inv_ids = self._match_invoice_payment_reference(
                        wiz_dict, st_line, cba, transaction, reconcile_note, free_comm
                    )

            if inv_ids:
                if len(inv_ids) == 1:
                    match_info["invoice_id"] = inv_ids[0]
                elif len(inv_ids) > 1:
                    line_notes = [
                        _(
                            "There are multiple invoices matching the "
                            "Invoice Amount and Reference."
                        )
                    ]
                    line_notes.append(_("A manual reconciliation is required."))
                    reconcile_note += self._format_line_notes(
                        wiz_dict, st_line, cba, transaction, line_notes
                    )

        if match_info.get("invoice_id"):
            match_info["status"] = "done"
            invoice = self.env["account.move"].browse(match_info["invoice_id"])
            partner = invoice.partner_id.commercial_partner_id
            match_info["partner_id"] = partner.id
            imls = invoice.line_ids.filtered(
                lambda r: r.account_type in ("asset_receivable", "liability_payable")
                and not r.reconciled
            )
            cur = cba.currency_id
            if cur == cba.company_id.currency_id:
                amt_fld = "amount_residual"
            elif cur == invoice.currency_id:
                amt_fld = "amount_residual_currency"
            else:
                line_notes = [
                    _(
                        "Invoice %(name)s matching Structured Communication '%(bba)s' "
                        "has another currency than this CODA file."
                    )
                    % {
                        "name": invoice.name,
                        "bba": transaction["struct_comm_bba"],
                    }
                ]
                line_notes.append(_("A manual reconciliation is required."))
                reconcile_note += self._format_line_notes(
                    wiz_dict, st_line, cba, transaction, line_notes
                )
                return reconcile_note

            matches = []
            iml_amt_total = 0.0
            for iml in imls:
                iml_amt = getattr(iml, amt_fld)
                iml_amt_total += iml_amt
                if cur.is_zero(iml_amt - transaction["amount"]):
                    matches.append(iml)
            if len(matches) == 1:
                aml = matches[0]
                match_info["counterpart_amls"] = [(aml, getattr(aml, amt_fld))]
            if not matches:
                if cur.is_zero(iml_amt_total - transaction["amount"]):
                    match_info["counterpart_amls"] = [
                        (aml, getattr(aml, amt_fld)) for aml in imls
                    ]
            if not match_info.get("counterpart_amls"):
                line_notes = [
                    _(
                        "Invoice %(name)s matching Structured Communication '%(bba)s' "
                        "has different residual amounts."
                    )
                    % {"name": invoice.name, "bba": transaction["struct_comm_bba"]}
                ]
                line_notes.append(_("A manual reconciliation is required."))
                reconcile_note += self._format_line_notes(
                    wiz_dict, st_line, cba, transaction, line_notes
                )
        return reconcile_note

    def _match_aml_other_domain_field(self, wiz_dict, st_line, cba, transaction):
        """
        Customise search input data and field.
        """
        search_field = "ref"
        search_input = repl_special(transaction["communication"].strip())
        return search_field, search_input

    def _match_aml_other_domain(self, wiz_dict, st_line, cba, transaction):

        search_field, search_input = self._match_aml_other_domain_field(
            wiz_dict, st_line, cba, transaction
        )
        if not search_field or not search_input:
            # skip resource intensive mathcing logic
            return None

        cpy_cur = cba.company_id.currency_id
        line_cur = st_line.currency_id or st_line.journal_currency_id
        if line_cur != cpy_cur and line_cur != cba.currency_id:
            return None

        domain = [
            (search_field, "=", search_input),
            ("parent_state", "=", "posted"),
            ("reconciled", "=", False),
            ("account_id.reconcile", "=", True),
            ("account_type", "not in", ("liability_payable", "asset_receivable")),
        ]
        amt_fld = "amount_residual"
        if line_cur == cba.currency_id and line_cur != cpy_cur:
            amt_fld = "amount_residual_currency"
        domain += [
            (amt_fld, ">=", transaction["amount"] - 0.005),
            (amt_fld, "<=", transaction["amount"] + 0.005),
        ]
        return domain

    def _match_aml_other(self, wiz_dict, st_line, cba, transaction, reconcile_note):
        """
        check matching with non payable/receivable open accounting entries.
        """
        match_info = transaction["matching_info"]
        if match_info["status"] in ["break", "done"]:
            return reconcile_note

        domain = self._match_aml_other_domain(wiz_dict, st_line, cba, transaction)
        if domain is None:
            return reconcile_note
        aml = self.env["account.move.line"].search(domain)

        if len(aml) == 1:
            match_info["status"] = "done"
            match_info["partner_id"] = aml.partner_id.id
            amt_fld = "amount_residual"
            if aml.currency_id == cba.currency_id:
                amt_fld = "amount_residual_currency"
            match_info["counterpart_amls"] = [(aml, getattr(aml, amt_fld))]

        return reconcile_note

    def _match_aml_arap_domain_field(self, wiz_dict, st_line, cba, transaction):
        """
        Customise search input data and field.

        The search field is different from the one used in the
        standard (manual) bank statement reconciliation.
        By default we search on the 'name' in stead of 'ref' field.

        The ref field is equal to the 'account.move,ref' field. We already
        cover this case in the invoice matching logic (executed before
        falling back to accounting entry matching).
        By a lookup on name, we allow to match on e.g. a set of
        open Payables/Receivables encoded manually or imported from
        an external accounting package
        (hence not generated from an Odoo invoice).
        """
        search_field = "name"
        search_input = transaction["communication"].strip()
        return search_field, search_input

    def _match_aml_arap_refine(self, wiz_dict, st_line, cba, transaction, amls):
        """
        Refine matching logic by parsing the 'search_field'.
        """
        search_field, search_input = self._match_aml_arap_domain_field(
            wiz_dict, st_line, cba, transaction
        )
        refined = self.env["account.move.line"]
        for aml in amls:
            aml_lookup_field = getattr(aml, search_field) or ""
            if transaction["struct_comm_bba"]:
                aml_lookup_field = re.sub(r"\D", "", aml_lookup_field)
                search_input = transaction["struct_comm_raw"].strip()
            if aml_lookup_field and search_input in aml_lookup_field:
                refined += aml
        return refined

    def _match_aml_arap_domain(self, wiz_dict, st_line, cba, transaction):
        """
        We assume that open items via miscellaneous entries are encoded in either
        company currency or bank statement currency, hence we return None for
        other cases (avoiding extra CPU time for currency conversions).
        """
        cpy_cur = cba.company_id.currency_id
        line_cur = st_line.currency_id or st_line.journal_currency_id
        if line_cur != cpy_cur and line_cur != cba.currency_id:
            return None
        domain = [
            ("parent_state", "=", "posted"),
            ("reconciled", "=", False),
            ("account_type", "in", ("liability_payable", "asset_receivable")),
            ("partner_id", "!=", False),
        ]
        amt_fld = "amount_residual"
        if line_cur == cba.currency_id and line_cur != cpy_cur:
            amt_fld = "amount_residual_currency"
        domain += [
            (amt_fld, ">=", transaction["amount"] - 0.005),
            (amt_fld, "<=", transaction["amount"] + 0.005),
        ]
        if cba.find_bbacom and cba.find_inv_number:
            # avoid double search on invoices
            domain.append(
                (
                    "move_id.move_type",
                    "not in",
                    ("out_invoice", "out_refund", "in_invoice", "in_refund"),
                )
            )
        return domain

    def _match_aml_arap(self, wiz_dict, st_line, cba, transaction, reconcile_note):
        """
        Check match with open payables/receivables.
        This matching logic can be very resource intensive for databases with
        a large number of unreconciled transactions.
        As a consequence this logic is by default disabled when creating a new
        'CODA Bank Account'.
        """
        match_info = transaction["matching_info"]
        if match_info["status"] in ["break", "done"]:
            return reconcile_note

        search_field, search_input = self._match_aml_arap_domain_field(
            wiz_dict, st_line, cba, transaction
        )
        if not search_field or not search_input:
            # skip resource intensive mathcing logic
            return reconcile_note

        domain = self._match_aml_arap_domain(wiz_dict, st_line, cba, transaction)
        if domain is None:
            return reconcile_note
        amls = self.env["account.move.line"].search(domain)

        aml = self._match_aml_arap_refine(wiz_dict, st_line, cba, transaction, amls)

        if len(aml) == 1:
            match_info["status"] = "done"
            match_info["partner_id"] = aml.partner_id.id
            amt_fld = "amount_residual"
            if aml.currency_id == cba.currency_id:
                amt_fld = "amount_residual_currency"
            match_info["counterpart_amls"] = [(aml, getattr(aml, amt_fld))]

        return reconcile_note

    def _match_account_move_line(
        self, wiz_dict, st_line, cba, transaction, reconcile_note
    ):
        """
        Match against open acounting entries.
        """
        match_info = transaction["matching_info"]
        if match_info["status"] in ["break", "done"]:
            return reconcile_note

        # exclude non-partner related transactions (e.g. bank costs)
        if not transaction["counterparty_number"]:
            return reconcile_note

        # match on open receivables/payables
        reconcile_note = self._match_aml_arap(
            wiz_dict, st_line, cba, transaction, reconcile_note
        )
        if match_info["status"] in ["break", "done"]:
            return reconcile_note

        # match on other open entries
        reconcile_note = self._match_aml_other(
            wiz_dict, st_line, cba, transaction, reconcile_note
        )
        if match_info["status"] in ["break", "done"]:
            return reconcile_note

        return reconcile_note

    def _match_counterparty(self, wiz_dict, st_line, cba, transaction, reconcile_note):
        match_info = transaction["matching_info"]
        if match_info["status"] in ["break", "done"]:
            return reconcile_note
        cp_number = transaction["counterparty_number"]
        if not cp_number:
            return reconcile_note

        transfer_accounts = [
            x for x in wiz_dict["company_bank_accounts"] if cp_number in x
        ]
        if transfer_accounts:
            # exclude transactions from
            # counterparty_number = bank account number of this statement
            if cp_number not in get_iban_and_bban(cba.bank_id.sanitized_acc_number):
                match_info["status"] = "done"
                match_info["account_id"] = cba.transfer_account_id.id
                match_info["transfer_account"] = True

        if match_info["status"] == "done" or not cba.find_partner:
            return reconcile_note

        partner_bank = self.env["res.partner.bank"].search(
            [
                ("sanitized_acc_number", "=", cp_number),
                ("partner_id.active", "=", True),
                "|",
                ("partner_id.parent_id", "=", False),
                ("partner_id.is_company", "=", True),
                "|",
                ("company_id", "=", False),
                ("company_id", "=", cba.company_id.id),
                "|",
                ("partner_id.company_id", "=", False),
                ("partner_id.company_id", "=", cba.company_id.id),
            ]
        )
        line_note = ""
        if partner_bank:
            if len(partner_bank) == 1:
                match_info["status"] = "done"
                match_info["bank_account_id"] = partner_bank.id
                match_info["partner_id"] = partner_bank.partner_id.id
            else:
                line_note = (
                    _(
                        "No partner record assigned: "
                        "There are multiple partners with the same "
                        "Bank Account Number '%s'!"
                    )
                    % cp_number
                )
        else:
            line_note = _(
                "The bank account '%(cp_number)s' is not defined "
                "for the partner '%(partner)s' !"
            ) % {"cp_number": cp_number, "partner": transaction["partner_name"]}
        if line_note:
            reconcile_note += self._format_line_notes(
                wiz_dict, st_line, cba, transaction, [line_note]
            )

        return reconcile_note

    def _unlink_duplicate_partner_banks(
        self, wiz_dict, st_line, cba, transaction, reconcile_note, partner_banks
    ):
        """
        Clean up partner bank duplicates, keep most recently created.
        This logic may conflict with factoring.
        We recommend to receive factoring payments via a separate bank account
        configured without partner bank update.
        """
        partner_bank_dups = partner_banks[:-1]
        partner = partner_banks[0].partner_id
        line_note = _(
            "Duplicate Bank Account(s) with account number '%(acc_number)s' "
            "for partner '%(partner)s' (id:%(pid)s) have been removed."
        ) % {
            "acc_number": partner_banks[0].acc_number,
            "partner": partner.name,
            "pid": partner.id,
        }
        reconcile_note += self._format_line_notes(
            wiz_dict, st_line, cba, transaction, [line_note], force=True
        )
        partner_bank_dups.unlink()
        return reconcile_note

    def _update_partner_bank(self, wiz_dict, st_line, cba, transaction, reconcile_note):
        """add bank account to partner record"""

        match_info = transaction["matching_info"]
        cp = transaction["counterparty_number"]
        if (
            match_info.get("partner_id")
            and cp
            and match_info.get("account_id") != cba.transfer_account_id.id
        ):
            partner_banks = self.env["res.partner.bank"].search(
                [
                    ("sanitized_acc_number", "=", cp),
                    ("partner_id", "=", match_info["partner_id"]),
                    "|",
                    ("company_id", "=", False),
                    ("company_id", "=", cba.company_id.id),
                ],
                order="id",
            )
            if len(partner_banks) > 1:
                reconcile_note = self._unlink_duplicate_partner_banks(
                    wiz_dict, st_line, cba, transaction, reconcile_note, partner_banks
                )

            if not partner_banks:
                feedback = self._create_res_partner_bank(
                    wiz_dict,
                    cba,
                    transaction["counterparty_bic"],
                    transaction["counterparty_number"],
                    match_info["partner_id"],
                    transaction["partner_name"],
                )
                if feedback:
                    reconcile_note += self._format_line_notes(
                        wiz_dict, st_line, cba, transaction, [feedback], force=True
                    )

        return reconcile_note

    def _format_line_notes(
        self, wiz_dict, st_line, cba, transaction, line_notes, force=False
    ):
        if not self.reconcile_matching_details and not force:
            return ""
        note = INDENT4
        note += _("Bank Statement '%(name)s' line '%(line_ref)s':") % {
            "name": st_line.statement_id.name,
            "line_ref": transaction["ref"],
        }
        for line_note in line_notes:
            line_note = line_note.replace("\n", INDENT8)
            note += INDENT8 + line_note
        return note

    def _prepare_new_aml_dict(self, wiz_dict, st_line, cba, transaction):
        match_info = transaction["matching_info"]
        ccur = st_line.company_id.currency_id
        jcur = st_line.journal_id.currency_id or ccur
        amt_fld = jcur == ccur and "balance" or "amount_currency"
        new_aml_dict = {
            "account_id": match_info["account_id"],
            "name": transaction["name"],
            amt_fld: -transaction["amount"],
        }
        if match_info.get("account_tax_id"):
            tax = self.env["account.tax"].browse(match_info["account_tax_id"])
            tag = tax.get_tax_tags(False, "base")
            new_aml_dict.update(
                {"tax_ids": [(6, 0, tax.ids)], "tax_tag_ids": [(6, 0, tag.ids)]}
            )
        else:
            new_aml_dict["tax_ids"] = []
        if match_info.get("analytic_distribution"):
            new_aml_dict["analytic_distribution"] = match_info["analytic_distribution"]
        return new_aml_dict

    def _prepare_counterpart_aml_dicts(self, wiz_dict, st_line, cba, transaction):
        match_info = transaction["matching_info"]
        ccur = st_line.company_id.currency_id
        jcur = st_line.journal_id.currency_id or ccur
        amt_fld = jcur == ccur and "balance" or "amount_currency"

        # rates provided in CODA transactions
        rate_c2j = rate_f2j = False
        if st_line.foreign_currency_id == ccur and st_line.amount_currency:
            rate_c2j = abs(st_line.amount / st_line.amount_currency)
        if st_line.foreign_currency_id != jcur and st_line.amount_currency:
            rate_f2j = abs(st_line.amount / st_line.amount_currency)

        counterpart_aml_dicts = []
        for entry in match_info["counterpart_amls"]:
            aml = entry[0]
            am_name = aml.move_id.name if aml.move_id.name != "/" else ""
            aml_name = aml.name or ""
            name = " ".join([am_name, aml_name])
            counterpart_aml_dict = {
                "counterpart_aml_id": aml.id,
                "account_id": aml.account_id.id,
                "name": name,
            }
            if aml.currency_id == jcur:
                counterpart_aml_dict[amt_fld] = -entry[1]
            elif aml.currency_id == ccur:
                counterpart_aml_dict[amt_fld] = -entry[1] * rate_c2j
            elif aml.currency_id == st_line.foreign_currency_id:
                counterpart_aml_dict[amt_fld] = -entry[1] * rate_f2j
            else:
                counterpart_aml_dict[amt_fld] = aml.currency_id._convert(
                    -entry[1], jcur, st_line.company_id, st_line.transaction_date
                )
            counterpart_aml_dicts.append(counterpart_aml_dict)
        return counterpart_aml_dicts

    def _create_move_and_reconcile(
        self, wiz_dict, st_line, cba, transaction, reconcile_note
    ):
        match_info = transaction["matching_info"]
        amls_vals = []
        if match_info.get("counterpart_amls"):
            amls_vals += self._prepare_counterpart_aml_dicts(
                wiz_dict, st_line, cba, transaction
            )
        if match_info.get("account_id"):
            amls_vals.append(
                self._prepare_new_aml_dict(wiz_dict, st_line, cba, transaction)
            )
        if amls_vals:
            st_line._reconcile(amls_vals)

        return reconcile_note

    def action_open_bank_statements(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "account_bank_statement_advanced.account_bank_statement_action"
        )
        domain = safe_eval(action.get("domain") or "[]")
        domain += [("id", "in", self.env.context.get("bank_statement_ids"))]
        action.update({"domain": domain})
        return action

    def action_open_coda_files(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "l10n_be_coda_advanced.account_coda_action"
        )
        domain = safe_eval(action.get("domain") or "[]")
        domain += [("id", "in", self.env.context.get("coda_ids"))]
        action.update({"domain": domain})
        return action

    def button_close(self):
        self.ensure_one()
        return {"type": "ir.actions.act_window_close"}

    def _get_st_line_name(self, wiz_dict, transaction):
        st_line_name = transaction["name"]

        if transaction["trans_family"] == "35" and transaction["trans_code"] in [
            "01",
            "37",
        ]:
            st_line_name = ", ".join(
                [
                    _("Closing"),
                    transaction["trans_code_desc"],
                    transaction["trans_category_desc"],
                ]
            )

        if transaction["trans_family"] in ["13", "41"]:
            st_line_name = ", ".join(
                [
                    transaction["trans_family_desc"],
                    transaction["trans_code_desc"],
                    transaction["trans_category_desc"],
                ]
            )

        if transaction["trans_family"] in ["80"]:
            st_line_name = ", ".join(
                [transaction["trans_code_desc"], transaction["trans_category_desc"]]
            )

        return st_line_name

    def _get_bank(self, wiz_dict, bic, iban):
        feedback = False
        country_code = iban[:2]
        bank = self.env["res.bank"]
        country = self.env["res.country"].search([("code", "=", country_code)])
        if not country:
            feedback = _(
                "\n        Bank lookup failed due to missing Country "
                "definition for Country Code '%s' !"
            ) % (country_code)
        else:
            bank_country = country[0]
            if iban[:2] == "BE":
                # To DO : extend for other countries
                bank_code = iban[4:7]
                if bic:
                    banks = self.env["res.bank"].search(
                        [
                            ("bic", "=", bic),
                            ("bban_code_list", "ilike", bank_code),
                            ("country", "=", bank_country.id),
                        ]
                    )
                    if banks:
                        bank = banks[0]
                    else:
                        bank = self.env["res.bank"].create(
                            {
                                "name": bic,
                                "code": bank_code,
                                "bic": bic,
                                "country": bank_country.id,
                            }
                        )
                else:
                    banks = self.env["res.bank"].search(
                        [("code", "=", bank_code), ("country", "=", bank_country.id)]
                    )
                    if banks:
                        bank = banks[0]
                        bic = bank.bic
                    else:
                        feedback = _(
                            "\n        Bank lookup failed. "
                            "Please define a Bank with "
                            "Code '%(bank_code)s' and Country '%(country)s' !"
                        ) % {"bank_code": bank_code, "country": bank_country.name}
            else:
                if not bic:
                    feedback = _(
                        "\n        Bank lookup failed due to missing BIC "
                        "in Bank Statement for IBAN '%s' !"
                    ) % (iban)
                else:
                    banks = self.env["res.bank"].search(
                        [("bic", "=", bic), ("country", "=", bank_country.id)]
                    )
                    if not banks:
                        bank_name = bic
                        bank = self.env["res.bank"].create(
                            {"name": bank_name, "bic": bic, "country": bank_country.id}
                        )
                    else:
                        bank = banks[0]

        bank_id = bank and bank.id or False
        bank_name = bank and bank.name or False
        return bank_id, bic, bank_name, feedback

    def _create_res_partner_bank(
        self, wiz_dict, cba, bic, iban, partner_id, partner_name
    ):
        bank_id = False
        feedback = False
        if check_iban(iban):
            bank_id, bic, bank_name, feedback = self._get_bank(wiz_dict, bic, iban)
            if not bank_id:
                return feedback
        else:
            # convert belgian BBAN numbers to IBAN
            if check_bban("BE", iban):
                kk = calc_iban_checksum("BE", iban)
                iban = "BE" + kk + iban
                bank_id, bic, bank_name, feedback = self._get_bank(wiz_dict, bic, iban)
                if not bank_id:
                    return feedback

        if bank_id:
            self.env["res.partner.bank"].create(
                {
                    "partner_id": partner_id,
                    "bank_id": bank_id,
                    "acc_type": "iban",
                    "acc_number": iban,
                    "company_id": cba.company_id.id,
                    "journal_id": False,
                    "sequence": 100,
                }
            )
        return feedback

    def _parse_comm_move(self, wiz_dict, coda_statement, transaction):
        comm_type = transaction["struct_comm_type"]
        method_name = "_parse_comm_move_" + comm_type
        if method_name in dir(self):
            method_instance = getattr(self, method_name)
            st_line_name, st_line_comm = method_instance(
                wiz_dict, coda_statement, transaction
            )
        else:  # To DO : '121', '122', '126'
            _logger.warning(
                "The parsing of Structured Commmunication Type %s "
                "has not yet been implemented. "
                "Please contact Noviat (info@noviat.com) for more information"
                " about the development roadmap",
                comm_type,
            )
            st_line_name = transaction["name"]
            st_line_comm = transaction["communication"]
        return st_line_name, st_line_comm

    def _parse_comm_move_100(self, wiz_dict, coda_statement, transaction):
        st_line_name = _("Payment with ISO 11649 structured format communication")
        comm = transaction["communication"]
        comm_fields = [
            {
                "name": "struct_comm_iso11649",
                "label": _("ISO 11649 Communication"),
                "value": comm.strip(),
            }
        ]
        line_note = (
            _(
                "Payment with a structured format communication "
                "applying the ISO standard 11649"
            )
            + ":"
        )
        line_note += INDENT8_HTML + _(
            "Structured creditor reference to remittance information"
        )
        st_line_name, st_line_comm = self._handle_struct_comm_details(
            wiz_dict, line_note, comm_fields, coda_statement, transaction
        )
        return st_line_name, st_line_comm

    def _parse_comm_move_101(self, wiz_dict, coda_statement, transaction):
        line_note = _(
            "Credit transfer or cash payment with " "structured format communication"
        )
        comm = transaction["communication"]
        st_line_name = bba_comm_formatted = (
            "+++" + comm[0:3] + "/" + comm[3:7] + "/" + comm[7:12] + "+++"
        )
        comm_fields = [
            {"name": "struct_comm_bba", "add_to_note": False, "value": comm[0:12]},
            {
                "name": "struct_comm_bba_formatted",
                "label": _("structured format communication"),
                "value": bba_comm_formatted,
            },
        ]
        line_note, st_line_comm = self._handle_struct_comm_details(
            wiz_dict, line_note, comm_fields, coda_statement, transaction
        )
        return st_line_name, st_line_comm

    def _parse_comm_move_102(self, wiz_dict, coda_statement, transaction):
        line_note = _(
            "Credit transfer or cash payment with reconstituted "
            "structured format communication"
        )
        comm = transaction["communication"]
        st_line_name = bba_comm_formatted = (
            "+++" + comm[0:3] + "/" + comm[3:7] + "/" + comm[7:12] + "+++"
        )
        comm_fields = [
            {"name": "struct_comm_bba", "add_to_note": False, "value": comm[0:12]},
            {
                "name": "struct_comm_bba_formatted",
                "label": _("structured format communication"),
                "value": bba_comm_formatted,
            },
        ]
        line_note, st_line_comm = self._handle_struct_comm_details(
            wiz_dict, line_note, comm_fields, coda_statement, transaction
        )
        return st_line_name, st_line_comm

    def _parse_comm_move_103(self, wiz_dict, coda_statement, transaction):
        comm = transaction["communication"]
        st_line_name = ", ".join([transaction["trans_family_desc"], _("Number")])
        comm_fields = [{"name": "number", "add_to_note": False, "value": comm.strip()}]
        self._handle_struct_comm_details(
            wiz_dict, st_line_name, comm_fields, coda_statement, transaction
        )
        st_line_comm = comm
        return st_line_name, st_line_comm

    def _parse_comm_move_105(self, wiz_dict, coda_statement, transaction):
        comm_type = transaction["struct_comm_type"]
        comm = transaction["communication"]
        st_line_name = (
            wiz_dict["comm_types"]
            .filtered(lambda r, t=comm_type: r.code == t)
            .description
        )
        amount = transaction.get("amount", 0.0)
        sign = amount < 0 and -1 or 1
        comm_fields = [
            {
                "name": "amount_currency_account",
                "label": _("Gross amount in the currency of the account"),
                "value": sign * list2float(comm[0:15]),
                "format": "{:0.2f}",
            },
            {
                "name": "amount_currency_original",
                "label": _("Gross amount in the original currency"),
                "value": sign * list2float(comm[15:30]),
                "format": "{:0.2f}",
            },
            {
                "name": "rate",
                "label": _("Rate"),
                "value": number2float(comm[30:42], 8),
                "format": "{:0.4f}",
            },
            {"name": "currency", "label": _("Currency"), "value": comm[42:45].strip()},
            {
                "name": "struct_format_comm",
                "label": _("Structured format communication"),
                "value": comm[45:57].strip(),
            },
            {
                "name": "country_code",
                "label": _("Country code of the principal"),
                "value": comm[57:59].strip(),
            },
            {
                "name": "amount_eur",
                "label": _("Equivalent in EUR"),
                "value": sign * list2float(comm[59:74]),
                "format": "{:0.2f}",
            },
        ]
        st_line_name, st_line_comm = self._handle_struct_comm_details(
            wiz_dict, st_line_name, comm_fields, coda_statement, transaction
        )
        return st_line_name, st_line_comm

    def _parse_comm_move_106(self, wiz_dict, coda_statement, transaction):
        st_line_name = _("VAT, withholding tax on income, commission, etc.")
        comm = transaction["communication"]
        comm_fields = [
            {
                "name": "amount_currency_account",
                "label": _("Equivalent in the currency of the account"),
                "value": list2float(comm[0:15]),
                "format": "{:0.2f}",
            },
            {
                "name": "tax_base_amount",
                "label": _("Amount on which % is calculated"),
                "value": list2float(comm[15:30]),
                "format": "{:0.2f}",
            },
            {
                "name": "percent",
                "label": _("Percent"),
                "value": number2float(comm[30:42], 8),
                "format": "{:0.4f}",
            },
        ]
        minimum = comm[42] == "1" and True or False
        label = minimum and _("Minimum applicable") or _("Minimum not applicable")
        comm_fields += [
            {"name": "minimum_applicable", "label": label, "value": comm[42]},
            {
                "name": "equivalent_eur",
                "label": _("Equivalent in EUR"),
                "value": list2float(comm[43:58]),
                "format": "{:0.2f}",
            },
        ]
        st_line_name, st_line_comm = self._handle_struct_comm_details(
            wiz_dict, st_line_name, comm_fields, coda_statement, transaction
        )
        return st_line_name, st_line_comm

    def _parse_comm_move_107(self, wiz_dict, coda_statement, transaction):
        """
        Structured communication 107 has been deleted as from CODA 2.4
        We keep the parsing method so that old CODA files can still be
        processed.
        """
        st_line_name = _("Direct debit - DOM'80")
        comm = transaction["communication"]
        paid_refusals = {
            "0": _("paid"),
            "1": _("direct debit cancelled or nonexistent"),
            "2": _("refusal - other reason"),
            "D": _("payer disagrees"),
            "E": _(
                "direct debit number linked to another "
                "identification number of the creditor"
            ),
        }
        comm_fields = [
            {
                "name": "direct_debit_number",
                "label": _("Direct Debit Number"),
                "value": comm[0:12].strip(),
            },
            {
                "name": "pivot_date",
                "label": _("Central (Pivot) Date"),
                "value": str2date(comm[12:18]),
            },
            {
                "name": "comm_zone",
                "label": _("Communication Zone"),
                "value": str2date(comm[18:48]),
            },
            {
                "name": "paid_refusal",
                "label": _("Paid or reason for refusal"),
                "value": paid_refusals.get(comm[48], ""),
            },
            {
                "name": "creditor_number",
                "label": _("Creditor's Number"),
                "value": comm[49:60].strip(),
            },
        ]
        st_line_name, st_line_comm = self._handle_struct_comm_details(
            wiz_dict, st_line_name, comm_fields, coda_statement, transaction
        )
        return st_line_name, st_line_comm

    def _parse_comm_move_108(self, wiz_dict, coda_statement, transaction):
        comm = transaction["communication"]
        period_from = str2date(comm[42:48])
        period_to = str2date(comm[48:54])
        st_line_name = _("Closing, period from %(period_from)s to %(period_to)s") % {
            period_from,
            period_to,
        }
        comm_fields = [
            {
                "name": "amount_currency_account",
                "label": _("Equivalent in the currency of the account"),
                "value": list2float(comm[0:15]),
                "format": "{:0.2f}",
            }
        ]
        interest = comm[30:42].strip("0")
        if interest:
            comm_fields += [
                {
                    "name": "calculation_basis",
                    "label": _("Interest rates, calculation basis"),
                    "value": list2float(comm[15:30]),
                    "format": "{:0.2f}",
                },
                {
                    "name": "interest",
                    "label": _("Interest"),
                    "value": list2float(comm[30:42]),
                    "format": "{:0.2f}",
                },
            ]
        comm_fields += [
            {"name": "period_from", "add_to_note": False, "value": period_from},
            {"name": "period_to", "add_to_note": False, "value": period_to},
        ]
        st_line_name, st_line_comm = self._handle_struct_comm_details(
            wiz_dict, st_line_name, comm_fields, coda_statement, transaction
        )
        return st_line_name, st_line_comm

    def _parse_comm_move_111(self, wiz_dict, coda_statement, transaction):
        st_line_name = _("POS credit - globalisation")
        comm = transaction["communication"]
        card_schemes = {
            "1": "Bancontact/Mister Cash",
            "2": _("Private"),
            "3": "Maestro",
            "5": "TINA",
            "9": _("Other"),
        }
        trans_types = {
            "0": _("Cumulative"),
            "1": _("Withdrawal"),
            "2": _("Cumulative on network"),
            "5": _("POS others"),
            "7": _("Distribution sector"),
            "8": _("Teledata"),
            "9": _("Fuel"),
        }
        comm_fields = [
            {
                "name": "card_scheme",
                "label": _("Card Scheme"),
                "value": card_schemes.get(comm[0], ""),
            },
            {
                "name": "pos_number",
                "label": _("POS Number"),
                "value": comm[1:7].strip(),
            },
            {
                "name": "period_number",
                "label": _("Period Number"),
                "value": comm[7:10].strip(),
            },
            {
                "name": "first_sequence_number",
                "label": _("First Transaction Sequence Number"),
                "value": comm[10:16].strip(),
            },
            {
                "name": "trans_first_date",
                "label": _("Date of first transaction"),
                "value": str2date(comm[16:22]),
            },
            {
                "name": "last_sequence_number",
                "label": _("Last Transaction Sequence Number"),
                "value": comm[22:28].strip(),
            },
            {
                "name": "trans_last_date",
                "label": _("Date of last transaction"),
                "value": str2date(comm[28:34]),
            },
            {
                "name": "trans_type",
                "label": _("Transaction Type"),
                "value": trans_types.get(comm[34], ""),
            },
        ]
        terminal_name = comm[35:50].strip()
        terminal_city = comm[51:60].strip()
        terminal_identification = ", ".join(
            [x for x in [terminal_name, terminal_city] if x]
        )
        comm_fields += [
            {"name": "terminal_name", "add_to_note": False, "value": terminal_name},
            {"name": "terminal_city", "add_to_note": False, "value": terminal_city},
            {
                "name": "terminal_identification",
                "label": _("Terminal Identification"),
                "value": terminal_identification,
            },
        ]
        st_line_name, st_line_comm = self._handle_struct_comm_details(
            wiz_dict, st_line_name, comm_fields, coda_statement, transaction
        )
        return st_line_name, st_line_comm

    def _parse_comm_move_113(self, wiz_dict, coda_statement, transaction):
        st_line_name = _("ATM/POS debit")
        comm = transaction["communication"]
        card_schemes = {
            "1": "Bancontact/Mister Cash",
            "2": "Maestro",
            "3": _("Private"),
            "9": _("Other"),
        }
        trans_types = {
            "1": _("Withdrawal"),
            "2": _("Proton loading"),
            "3": _("Reimbursement Proton balance"),
            "4": _("Reversal of purchases"),
            "5": _("POS others"),
            "7": _("Distribution sector"),
            "8": _("Teledata"),
            "9": _("Fuel"),
        }
        product_codes = {
            "01": _("premium with lead substitute"),
            "02": _("europremium"),
            "03": _("diesel"),
            "04": _("LPG"),
            "06": _("premium plus 98 oct"),
            "07": _("regular unleaded"),
            "08": _("domestic fuel oil"),
            "09": _("lubricants"),
            "10": _("petrol"),
            "11": _("premium 99+"),
            "12": _("Avgas"),
            "16": _("other types"),
        }
        comm_fields = [
            {
                "name": "card_number",
                "label": _("Card Number"),
                "value": comm[0:16].strip(),
            },
            {
                "name": "card_scheme",
                "label": _("Card Scheme"),
                "value": card_schemes.get(comm[16], ""),
            },
            {
                "name": "terminal_number",
                "label": _("Terminal Number"),
                "value": comm[17:23].strip(),
            },
            {
                "name": "sequence_number",
                "label": _("Transaction Sequence Number"),
                "value": comm[23:29].strip(),
            },
        ]
        trans_date = comm[29:35].strip()
        trans_date = trans_date and str2date(trans_date)
        trans_hour = comm[35:39].strip()
        trans_hour = trans_hour and str2time(trans_hour)
        trans_time = " ".join([x for x in [trans_date, trans_hour] if x])
        comm_fields += [
            {"name": "transaction_date", "add_to_note": False, "value": trans_date},
            {"name": "transaction_hour", "add_to_note": False, "value": trans_hour},
            {"name": "transaction_time", "label": _("Time"), "value": trans_time},
            {
                "name": "trans_type",
                "label": _("Transaction Type"),
                "value": trans_types.get(comm[39], ""),
            },
        ]
        terminal_name = comm[40:56].strip()
        terminal_city = comm[56:66].strip()
        terminal_identification = ", ".join(
            [x for x in [terminal_name, terminal_city] if x]
        )
        comm_fields += [
            {"name": "terminal_name", "add_to_note": False, "value": terminal_name},
            {"name": "terminal_city", "add_to_note": False, "value": terminal_city},
            {
                "name": "terminal_identification",
                "label": _("Terminal Identification"),
                "value": terminal_identification,
            },
        ]
        orig_amount = comm[66:81].strip() and list2float(comm[66:81])
        if orig_amount:
            comm_fields += [
                {
                    "name": "orig_amount",
                    "label": _("Original Amount"),
                    "value": orig_amount,
                    "format": "{:0.2f}",
                },
                {
                    "name": "rate",
                    "label": _("Rate"),
                    "value": number2float(comm[81:93], 8),
                    "format": "{:0.2f}",
                },
                {"name": "currency", "label": _("Currency"), "value": comm[93:96]},
            ]
        comm_fields += [
            {
                "name": "volume",
                "label": _("Volume"),
                "value": number2float(comm[96:101], 2),
                "format": "{:0.2f}",
            },
            {
                "name": "product_code",
                "label": _("Product Code"),
                "value": product_codes.get(comm[101:103], ""),
            },
            {
                "name": "unit_price",
                "label": _("Unit Price"),
                "value": number2float(comm[103:108], 2),
                "format": "{:0.2f}",
            },
        ]
        st_line_name, st_line_comm = self._handle_struct_comm_details(
            wiz_dict, st_line_name, comm_fields, coda_statement, transaction
        )
        return st_line_name, st_line_comm

    def _parse_comm_move_114(self, wiz_dict, coda_statement, transaction):
        st_line_name = _("POS credit - individual transaction")
        comm = transaction["communication"]
        card_schemes = {
            "1": "Bancontact/Mister Cash",
            "2": "Maestro",
            "3": _("Private"),
            "5": "TINA",
            "9": _("Other"),
        }
        trans_types = {
            "1": _("Withdrawal"),
            "5": _("POS others"),
            "7": _("Distribution sector"),
            "8": _("Teledata"),
            "9": _("Fuel"),
        }
        comm_fields = [
            {
                "name": "card_scheme",
                "label": _("Card Scheme"),
                "value": card_schemes.get(comm[0], ""),
            },
            {
                "name": "pos_number",
                "label": _("POS Number"),
                "value": comm[1:7].strip(),
            },
            {
                "name": "period_number",
                "label": _("Period Number"),
                "value": comm[7:10].strip(),
            },
            {
                "name": "sequence_number",
                "label": _("Transaction Sequence Number"),
                "value": comm[10:16].strip(),
            },
        ]
        trans_date = comm[16:22].strip()
        trans_date = trans_date and str2date(trans_date)
        trans_hour = comm[22:26].strip()
        trans_hour = trans_hour and str2time(trans_hour)
        trans_time = " ".join([x for x in [trans_date, trans_hour] if x])
        comm_fields += [
            {"name": "transaction_date", "add_to_note": False, "value": trans_date},
            {"name": "transaction_hour", "add_to_note": False, "value": trans_hour},
            {"name": "transaction_time", "label": _("Time"), "value": trans_time},
            {
                "name": "trans_type",
                "label": _("Transaction Type"),
                "value": trans_types.get(comm[26], ""),
            },
        ]
        terminal_name = comm[27:43].strip()
        terminal_city = comm[43:53].strip()
        terminal_identification = ", ".join(
            [x for x in [terminal_name, terminal_city] if x]
        )
        comm_fields += [
            {"name": "terminal_name", "add_to_note": False, "value": terminal_name},
            {"name": "terminal_city", "add_to_note": False, "value": terminal_city},
            {
                "name": "terminal_identification",
                "label": _("Terminal Identification"),
                "value": terminal_identification,
            },
            {
                "name": "trans_reference",
                "label": _("Transaction Reference"),
                "value": comm[53:69].strip(),
            },
        ]
        st_line_name, st_line_comm = self._handle_struct_comm_details(
            wiz_dict, st_line_name, comm_fields, coda_statement, transaction
        )
        return st_line_name, st_line_comm

    def _parse_comm_move_115(self, wiz_dict, coda_statement, transaction):
        st_line_name = _("Terminal cash deposit")
        comm = transaction["communication"]
        card_schemes = {"2": _("Private"), "9": _("Other")}
        comm_fields = [
            {
                "name": "card_number",
                "label": _("Card Number"),
                "value": comm[:16].strip(),
            },
            {
                "name": "card_scheme",
                "label": _("Card Scheme"),
                "value": card_schemes.get(comm[16], ""),
            },
            {
                "name": "terminal_number",
                "label": _("Terminal Number"),
                "value": comm[17:23].strip(),
            },
            {
                "name": "sequence_number",
                "label": _("Transaction Sequence Number"),
                "value": comm[23:29].strip(),
            },
        ]
        payment_day = comm[29:35].strip()
        payment_hour = comm[35:39].strip()
        payment_time = " ".join([x for x in [payment_day, payment_hour] if x])
        comm_fields += [
            {"name": "payment_day", "add_to_note": False, "value": payment_day},
            {"name": "payment_hour", "add_to_note": False, "value": payment_hour},
            {"name": "payment_time", "label": _("Time"), "value": payment_time},
            {
                "name": "validation_date",
                "label": _("Validation Date"),
                "value": comm[39:45].strip(),
            },
            {
                "name": "validation_sequence_number",
                "label": _("Validation Sequence Number"),
                "value": comm[45:51].strip(),
            },
            {
                "name": "amount",
                "label": _("Amount (given by the customer)"),
                "value": list2float(comm[51:66]),
                "format": "{:0.2f}",
            },
            {
                "name": "conformity_code",
                "label": _("Conformity Code"),
                "value": comm[66].strip(),
            },
        ]
        terminal_name = comm[67:83].strip()
        terminal_city = comm[83:93].strip()
        terminal_identification = ", ".join(
            [x for x in [terminal_name, terminal_city] if x]
        )
        comm_fields += [
            {"name": "terminal_name", "add_to_note": False, "value": terminal_name},
            {"name": "terminal_city", "add_to_note": False, "value": terminal_city},
            {
                "name": "terminal_identification",
                "label": _("Terminal Identification"),
                "value": terminal_identification,
            },
            {"name": "message", "label": _("Message"), "value": comm[93:105].strip()},
        ]
        st_line_name, st_line_comm = self._handle_struct_comm_details(
            wiz_dict, st_line_name, comm_fields, coda_statement, transaction
        )
        return st_line_name, st_line_comm

    def _parse_comm_move_123(self, wiz_dict, coda_statement, transaction):
        comm = transaction["communication"]
        st_line_name = transaction["name"]
        comm_fields = [
            {
                "name": "starting_date",
                "label": _("Starting Date"),
                "value": str2date(comm[0:6]),
            }
        ]
        maturity_date = (
            comm[6:12] == "999999"
            and _("guarantee without fixed term")
            or str2date(comm[0:6])
        )
        comm_fields += [
            {
                "name": "maturity_date",
                "label": _("Maturity Date"),
                "value": maturity_date,
            },
            {
                "name": "basic_amount",
                "label": _("Basic Amount"),
                "value": list2float(comm[12:27]),
                "format": "{:0.2f}",
            },
            {
                "name": "percent",
                "label": _("Percentage"),
                "value": number2float(comm[27:39], 8),
                "format": "{:0.4f}",
            },
            {
                "name": "term",
                "label": _("Term in days"),
                "value": comm[39:43].lstrip("0"),
            },
        ]
        minimum = comm[43] == "1" and True or False
        label = minimum and _("Minimum applicable") or _("Minimum not applicable")
        comm_fields += [
            {"name": "minimum_applicable", "label": label, "value": comm[43]},
            {
                "name": "guarantee_number",
                "label": _("Guarantee Number"),
                "value": comm[44:57].strip(),
            },
        ]
        st_line_name, st_line_comm = self._handle_struct_comm_details(
            wiz_dict, st_line_name, comm_fields, coda_statement, transaction
        )
        return st_line_name, st_line_comm

    def _parse_comm_move_124(self, wiz_dict, coda_statement, transaction):
        st_line_name = _("Settlement credit cards")
        comm = transaction["communication"]
        card_issuers = {
            "1": "Mastercard",
            "2": "Visa",
            "3": "American Express",
            "4": "Diners Club",
            "9": _("Other"),
        }
        comm_fields = [
            {
                "name": "card_number",
                "label": _("Card Number"),
                "value": comm[0:20].strip(),
            },
            {
                "name": "card_issuer",
                "label": _("Issuing Institution"),
                "value": card_issuers.get(comm[20], ""),
            },
            {
                "name": "invoice_number",
                "label": _("Invoice Number"),
                "value": comm[21:33].strip(),
            },
            {
                "name": "identification_number",
                "label": _("Identification Number"),
                "value": comm[33:48].strip(),
            },
            {
                "name": "date",
                "label": _("Date"),
                "value": comm[48:54].strip() and str2date(comm[48:54]) or "",
            },
        ]
        st_line_name, st_line_comm = self._handle_struct_comm_details(
            wiz_dict, st_line_name, comm_fields, coda_statement, transaction
        )
        return st_line_name, st_line_comm

    def _parse_comm_move_125(self, wiz_dict, coda_statement, transaction):
        comm = transaction["communication"]
        st_line_name = transaction["name"]
        if transaction["trans_family"] not in ST_LINE_NAME_FAMILIES:
            st_line_name = _("Credit")
        credit_account = comm[0:27].strip()
        credit_account_formatted = credit_account
        if check_bban("BE", credit_account):
            credit_account_formatted = "-".join(
                [credit_account[:3], credit_account[3:10], credit_account[10:]]
            )
        comm_fields = [
            {"name": "credit_account", "add_to_note": False, "value": credit_account},
            {
                "name": "credit_account_formatted",
                "label": _("Credit Account Number"),
                "value": credit_account_formatted,
            },
            {
                "name": "old_balance",
                "label": _("Old Balance"),
                "value": list2float(comm[27:42]),
                "format": "{:0.2f}",
            },
            {
                "name": "new_balance",
                "label": _("New Balance"),
                "value": list2float(comm[42:57]),
                "format": "{:0.2f}",
            },
            {
                "name": "amount",
                "label": _("Amount"),
                "value": list2float(comm[57:72]),
                "format": "{:0.2f}",
            },
            {"name": "currency", "label": _("Currency"), "value": comm[72:75]},
            {"name": "start_date", "label": _("Starting Date"), "value": comm[75:81]},
            {"name": "end_date", "label": _("End Date"), "value": comm[81:87]},
            {
                "name": "rate",
                "label": _("Nominal Interest Rate or Rate of Charge"),
                "value": number2float(comm[87:99], 8),
                "format": "{:0.4f}",
            },
            {
                "name": "trans_reference",
                "label": _("Transaction Reference"),
                "value": comm[99:112].strip(),
            },
        ]
        st_line_name, st_line_comm = self._handle_struct_comm_details(
            wiz_dict, st_line_name, comm_fields, coda_statement, transaction
        )
        return st_line_name, st_line_comm

    def _parse_comm_move_127(self, wiz_dict, coda_statement, transaction):
        st_line_name = _("European direct debit (SEPA)")
        comm = transaction["communication"]
        direct_debit_types = {
            "0": _("unspecified"),
            "1": _("recurrent"),
            "2": _("one-off"),
            "3": _("1-st (recurrent)"),
            "4": _("last (recurrent)"),
        }
        direct_debit_schemes = {
            "0": _("unspecified"),
            "1": _("SEPA core"),
            "2": _("SEPA B2B"),
        }
        paid_refusals = {
            "0": _("paid"),
            "1": _("technical problem"),
            "2": _("refusal - reason not specified"),
            "3": _("debtor disagrees"),
            "4": _("debtor's account problem"),
        }
        R_types = {
            "0": _("paid"),
            "1": _("reject"),
            "2": _("return"),
            "3": _("refund"),
            "4": _("reversal"),
            "5": _("cancellation"),
        }
        comm_fields = [
            {
                "name": "settlement_date",
                "label": _("Settlement Date"),
                "value": str2date(comm[0:6]),
            },
            {
                "name": "direct_debit_type",
                "label": _("Direct Debit Type"),
                "value": direct_debit_types.get(comm[6], ""),
            },
            {
                "name": "direct_debit_scheme",
                "label": _("Direct Debit Scheme"),
                "value": direct_debit_schemes.get(comm[7], ""),
            },
            {
                "name": "paid_refusal",
                "label": _("Paid or reason for refusal"),
                "value": paid_refusals.get(comm[8], ""),
            },
            {
                "name": "creditor_id",
                "label": _("Creditor's Identification Code"),
                "value": comm[9:44].strip(),
            },
            {
                "name": "mandate_ref",
                "label": _("Mandate Reference"),
                "value": comm[44:79].strip(),
            },
            {
                "name": "comm_zone",
                "label": _("Communication"),
                "value": comm[79:141].strip(),
            },
            {
                "name": "R_type",
                "label": _("R transaction Type"),
                "value": R_types.get(comm[141], ""),
            },
            {"name": "reason", "label": _("Reason"), "value": comm[142:146].strip()},
        ]
        st_line_name, st_line_comm = self._handle_struct_comm_details(
            wiz_dict, st_line_name, comm_fields, coda_statement, transaction
        )
        return st_line_name, st_line_comm

    def _handle_struct_comm_details(
        self, wiz_dict, st_line_name, comm_fields, coda_statement, transaction
    ):
        """
        Use this method to customise the presentation of the
        structured communication transaction details.
        """
        comm_fields = [f for f in comm_fields if f.get("value")]
        transaction["struct_comm_details"] = {
            x["name"]: x["value"] for x in comm_fields
        }
        st_line_comm = "\n" + INDENT8_HTML + st_line_name
        for comm_field in comm_fields:
            if not comm_field.get("add_to_note", True):
                continue
            st_line_comm += INDENT8_HTML
            label = comm_field.get("label", "")
            if label:
                st_line_comm += label + ": "
            fmt = comm_field.get("format") or "{}"
            st_line_comm += fmt.format(comm_field.get("value"))
        return st_line_name, st_line_comm

    def _parse_comm_info(self, wiz_dict, coda_statement, transaction):
        comm_type = transaction["struct_comm_type"]
        method_name = "_parse_comm_info_" + comm_type
        if method_name in dir(self):
            method_instance = getattr(self, method_name)
            st_line_name, st_line_comm = method_instance(
                wiz_dict, coda_statement, transaction
            )
        else:  # To DO : 010, 011
            _logger.warning(
                "The parsing of Structured Commmunication Type %s "
                "has not yet been implemented. "
                "Please contact Noviat (info@noviat.com) for "
                "more information about the development roadmap",
                comm_type,
            )
            st_line_name = transaction["name"]
            st_line_comm = "\n" + INDENT8_HTML + st_line_name
            st_line_comm += "\n" + INDENT8_HTML + transaction["communication"]
        return st_line_name, st_line_comm

    def _parse_comm_info_001(self, wiz_dict, coda_statement, transaction):
        comm_type = transaction["struct_comm_type"]
        comm = transaction["communication"]
        st_line_name = (
            wiz_dict["comm_types"]
            .filtered(lambda r, t=comm_type: r.code == t)
            .description
        )
        st_line_comm = INDENT8_HTML + st_line_name + ":"
        val = comm[0:70].strip()
        if val:
            st_line_comm += INDENT8_HTML + _("Name") + ": %s" % val
        val = comm[70:105].strip()
        if val:
            st_line_comm += INDENT8_HTML + _("Street") + ": %s" % val
        val = comm[105:140].strip()
        if val:
            st_line_comm += INDENT8_HTML + _("Locality") + ": %s" % val
        val = comm[140:175].strip()
        if val:
            st_line_comm += INDENT8_HTML + _("Identification Code") + ": %s" % val
        return st_line_name, st_line_comm

    def _parse_comm_info_002(self, wiz_dict, coda_statement, transaction):
        comm_type = transaction["struct_comm_type"]
        comm = transaction["communication"]
        st_line_name = (
            wiz_dict["comm_types"]
            .filtered(lambda r, t=comm_type: r.code == t)
            .description
        )
        st_line_comm = comm.strip()
        return st_line_name, st_line_comm

    def _parse_comm_info_004(self, wiz_dict, coda_statement, transaction):
        comm_type = transaction["struct_comm_type"]
        comm = transaction["communication"]
        st_line_name = (
            wiz_dict["comm_types"]
            .filtered(lambda r, t=comm_type: r.code == t)
            .description
        )
        st_line_comm = comm.strip()
        return st_line_name, st_line_comm

    def _parse_comm_info_005(self, wiz_dict, coda_statement, transaction):
        comm_type = transaction["struct_comm_type"]
        comm = transaction["communication"]
        st_line_name = (
            wiz_dict["comm_types"]
            .filtered(lambda r, t=comm_type: r.code == t)
            .description
        )
        st_line_comm = comm.strip()
        return st_line_name, st_line_comm

    def _parse_comm_info_006(self, wiz_dict, coda_statement, transaction):
        comm_type = transaction["struct_comm_type"]
        comm = transaction["communication"]
        amount_sign = comm[48]
        amount = (
            (amount_sign == "1" and "-" or "")
            + ("%.2f" % list2float(comm[33:48]))
            + " "
            + comm[30:33]
        )
        st_line_name = (
            wiz_dict["comm_types"]
            .filtered(lambda r, t=comm_type: r.code == t)
            .description
        )
        st_line_comm = INDENT8_HTML + st_line_name + ":"
        st_line_comm += (
            INDENT8_HTML + _("Description of the detail") + ": %s" % comm[0:30].strip()
        )
        st_line_comm += INDENT8_HTML + _("Amount") + ": %s" % amount
        st_line_comm += INDENT8_HTML + _("Category") + ": %s" % comm[49:52].strip()
        return st_line_name, st_line_comm

    def _parse_comm_info_007(self, wiz_dict, coda_statement, transaction):
        comm_type = transaction["struct_comm_type"]
        comm = transaction["communication"]
        st_line_name = (
            wiz_dict["comm_types"]
            .filtered(lambda r, t=comm_type: r.code == t)
            .description
        )
        st_line_comm = INDENT8_HTML + st_line_name + ":"
        st_line_comm += INDENT8_HTML + _("Number of notes/coins") + ": %s" % comm[0:7]
        st_line_comm += INDENT8_HTML + _("Note/coin denomination") + ": %s" % comm[7:13]
        st_line_comm += (
            INDENT8_HTML + _("Total amount") + ": %.2f" % list2float(comm[13:28])
        )
        return st_line_name, st_line_comm

    def _parse_comm_info_008(self, wiz_dict, coda_statement, transaction):
        comm_type = transaction["struct_comm_type"]
        comm = transaction["communication"]
        st_line_name = (
            wiz_dict["comm_types"]
            .filtered(lambda r, t=comm_type: r.code == t)
            .description
        )
        st_line_comm = INDENT8_HTML + st_line_name + ":"
        st_line_comm += INDENT8_HTML + _("Name") + ": %s" % comm[0:70].strip()
        st_line_comm += (
            INDENT8_HTML + _("Identification Code") + ": %s" % comm[70:105].strip()
        )
        return st_line_name, st_line_comm

    def _parse_comm_info_009(self, wiz_dict, coda_statement, transaction):
        comm_type = transaction["struct_comm_type"]
        comm = transaction["communication"]
        st_line_name = (
            wiz_dict["comm_types"]
            .filtered(lambda r, t=comm_type: r.code == t)
            .description
        )
        st_line_comm = INDENT8_HTML + st_line_name + ":"
        st_line_comm += INDENT8_HTML + _("Name") + ": %s" % comm[0:70].strip()
        st_line_comm += (
            INDENT8_HTML + _("Identification Code") + ": %s" % comm[70:105].strip()
        )
        return st_line_name, st_line_comm
