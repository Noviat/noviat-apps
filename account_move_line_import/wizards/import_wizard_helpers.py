# Copyright 2009-2021 Noviat
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import time
from datetime import datetime

import xlrd


def dialect2dict(dialect):
    attrs = [
        "delimiter",
        "doublequote",
        "escapechar",
        "lineterminator",
        "quotechar",
        "quoting",
        "skipinitialspace",
    ]
    return {k: getattr(dialect, k) for k in attrs}


def cell_is_int(cell):
    is_int = False
    if cell.ctype == xlrd.XL_CELL_NUMBER:
        is_int = cell.value % 1 == 0.0
    elif cell.ctype == xlrd.XL_CELL_TEXT:
        try:
            int(cell.value)
        except Exception:
            pass
    return is_int


def cell2char(cell):
    if cell.ctype == xlrd.XL_CELL_TEXT:
        val = cell.value
    elif cell.ctype == xlrd.XL_CELL_NUMBER:
        is_int = cell.value % 1 == 0.0
        if is_int:
            val = str(int(cell.value))
        else:
            val = str(cell.value)
    else:
        val = str(cell.value)
    return val


def cell2float(cell):
    if cell.ctype == xlrd.XL_CELL_TEXT:
        amount = cell.value
        decimal_separator = "."
        dot_i = amount.rfind(".")
        comma_i = amount.rfind(",")
        if comma_i > dot_i and comma_i > 0:
            decimal_separator = ","
        val = str2float(amount, decimal_separator)
    else:
        val = cell.value
    return val


def cell2bool(cell):
    val = None
    if cell.ctype == xlrd.XL_CELL_TEXT:
        val = cell.value.capitalize().strip()
        if val in ["", "0", "False"]:
            val = False
        elif val in ["1", "True"]:
            val = True
    else:
        is_int = cell.value % 1 == 0.0
        if is_int:
            val = val == 1 and True or False
    return val


def cell2date(cell, datemode=0):
    """
    :param datemode: workbook.datemode, cf. https://xlrd.readthedocs.io
    """
    val = None
    if cell.ctype == xlrd.XL_CELL_TEXT:
        if cell.value:
            val = str2date(cell.value) or None
    elif cell.ctype in [xlrd.XL_CELL_NUMBER, xlrd.XL_CELL_DATE]:
        val = xlrd.xldate.xldate_as_tuple(cell.value, datemode)
        val = datetime(*val).strftime("%Y-%m-%d")
    return val


def str2float(amount, decimal_separator):
    if not amount:
        return 0.0
    try:
        if decimal_separator == ".":
            return float(amount.replace(",", ""))
        else:
            return float(amount.replace(".", "").replace(",", "."))
    except Exception:
        return False


def str2int(amount, decimal_separator):
    if not amount:
        return 0
    try:
        if decimal_separator == ".":
            return int(amount.replace(",", ""))
        else:
            return int(amount.replace(".", "").replace(",", "."))
    except Exception:
        return False


def str2date(date_str):
    try:
        return time.strftime("%Y-%m-%d", time.strptime(date_str, "%Y-%m-%d"))
    except Exception:
        return False
