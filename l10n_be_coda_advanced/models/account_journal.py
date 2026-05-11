# Copyright 2009-2025 Noviat.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import re
from sys import exc_info
from traceback import format_exception

from odoo import _, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def _check_coda_format(self, data):
        # Matches the first 24 characters of a CODA file, as defined by the
        # febelfin specifications
        try:
            data_decoded = data.decode()
        except Exception:
            return False
        return re.match(r"0{5}\d{9}05[ D] +", data_decoded)

    def _import_bank_statement(self, attachments):
        """
        Use the CODA parser of this module when using the Odoo Enterprise
        standard statement import for journals with a 'coda.bank.account' config.
        """
        import_results = []
        bank_statement_ids = []
        err_string = ""

        # super() if not coda format
        attachs_decoded = []
        for att in attachments:
            att_decoded = base64.b64decode(att.datas)
            if not self._check_coda_format(att_decoded[:24]):
                return super()._import_bank_statement(attachments)
            attachs_decoded.append(att_decoded)

        # we don't cover the use case of non "windows-1252" codepages when
        # using the standard Odoo Enterprise import wizard
        wiz_vals = {"codepage": "windows-1252"}
        for i, att in enumerate(attachments):
            try:
                wiz_dict = {}
                codafile = attachs_decoded[i]
                codafilename = att.name
                wiz = self.env["account.coda.import"].create(wiz_vals)
                coda, statements, note = wiz._coda_parsing(
                    wiz_dict, codafile, codafilename
                )
                err_string += wiz_dict.get("err_string", "")
                if not wiz_dict.get("coda_banks"):
                    # super() if no 'coda.bank.account' config is found
                    no_cba = super()._import_bank_statement(attachments)
                    domain = no_cba.get("domain", [])
                    for entry in domain:
                        if (
                            isinstance(entry, tuple)
                            and entry[0] == "statement_id"
                            and entry[1] == "in"
                        ):
                            bank_statement_ids += entry[2]
                else:
                    import_results += [(coda, statements, note)]
                    bank_statement_ids += statements.ids
            except (UserError, ValidationError) as e:
                error = _(
                    "\n\nError while processing CODA File '%(fn)s' :\n%(err_msg)s"
                ) % {
                    "fn": codafilename,
                    "err_msg": "".join(e.args),
                }
                import_results += [
                    (
                        self.env["account.coda"],
                        self.env["account.bank.statement"],
                        error,
                    )
                ]
                err_string += error
            except Exception:
                tb = "".join(format_exception(*exc_info()))
                error = _("\n\nError while processing CODA File '%(fn)s' :\n%(tb)s") % {
                    "fn": codafilename,
                    "tb": tb,
                }
                import_results += [
                    (
                        self.env["account.coda"],
                        self.env["account.bank.statement"],
                        error,
                    )
                ]
                err_string += error

        for entry in import_results:
            statements = entry[1]
            for statement in statements:
                wiz = wiz.with_company(statement.company_id)
                statement = statement.with_company(statement.company_id)
                wiz._automatic_reconcile(wiz_dict, statement)

        if bank_statement_ids:
            action = self.env["ir.actions.act_window"]._for_xml_id(
                "account_bank_statement_advanced.account_bank_statement_action"
            )
            action["display_name"] = _("Imported Bank Statements")
            domain = safe_eval(action.get("domain") or "[]")
            domain += [("id", "in", bank_statement_ids)]
            action.update({"domain": domain})
            return action
        else:
            message = _("No Bank Statements imported.") + err_string
            raise UserError(message)
