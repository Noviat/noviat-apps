# Copyright 2009-2020 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Belgium - provinces',
    'version': '13.0.1.0.0',
    'license': 'AGPL-3',
    'author': 'Noviat',
    'category': 'Localization',
    'summary': 'Belgium - provinces',
    'depends': [
        'base',
    ],
    'data': [
        'data/res_country_state_data.xml',
    ],
    'installable': True,
    'pre_init_hook': 'update_country_state_refs',
}
