# Copyright 2009-2019 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Journal Items Search Extension',
    'version': '12.0.1.0.0',
    'license': 'AGPL-3',
    'author': 'Noviat',
    'website': 'http://www.noviat.com',
    'category': 'Accounting & Finance',
    'depends': [
        'account',
        'date_range'
    ],
    'data': [
        'views/account_move_line_views.xml',
        'views/assets_backend.xml',
    ],
    'qweb': [
        'static/src/xml/amlse.xml',
    ],
    'installable': True,
}
