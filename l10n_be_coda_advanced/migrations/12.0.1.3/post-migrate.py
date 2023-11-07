# Copyright 2009-2020 Noviat.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import base64
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    codas = env["account.coda"].search([])
    for coda in codas:
        data = coda.coda_data
        if data and not is_base64(data):
            coda.coda_data = base64.b64encode(data)
            _logger.warning(
                "CODA File %s (%s) has been repaired",
                coda.name,
                coda.coda_creation_date,
            )


def is_base64(data):
    try:
        data = data.replace(b"\n", b"")
        return data == base64.b64encode(base64.b64decode(data))
    except Exception:
        return False
