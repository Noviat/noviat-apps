# Copyright 2009-2021 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from lxml import etree

from odoo import _, api, models
from odoo.exceptions import UserError


class AccountPaymentOrder(models.Model):
    _inherit = "account.payment.order"

    @api.model
    def generate_party_agent(
        self, parent_node, party_type, order, partner_bank, gen_args, bank_line=None
    ):
        res = super().generate_party_agent(
            parent_node, party_type, order, partner_bank, gen_args, bank_line=bank_line
        )
        if party_type == "Cdtr" and parent_node.tag == "CdtTrfTxInf":
            csmi = partner_bank.bank_id.clearing_system_member_identification
            csi = partner_bank.bank_id.country.clearing_system_identification
            if csmi and csi:
                FinInstnId = parent_node.xpath("CdtrAgt/FinInstnId")
                if not FinInstnId:
                    raise UserError(_("Missing FinInstId tag."))
                FinInstnId = FinInstnId[0]
                ClrSysMmbId = etree.SubElement(FinInstnId, "ClrSysMmbId")
                ClrSysId = etree.SubElement(ClrSysMmbId, "ClrSysId")
                Cd = etree.SubElement(ClrSysId, "Cd")
                Cd.text = csi
                MmbId = etree.SubElement(ClrSysMmbId, "MmbId")
                MmbId.text = csmi
        return res
