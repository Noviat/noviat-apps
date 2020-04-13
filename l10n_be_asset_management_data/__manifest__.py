# Copyright 2009-2020 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Asset Management - Belgian reporting structure',
    'version': '12.0.1.0.0',
    'license': 'AGPL-3',
    'author': 'Noviat',
    'website': 'http://www.noviat.com',
    'category': 'Accounting & Finance',
    'complexity': 'normal',
    'summary': 'Asset Management - Belgian reporting structure',
    'depends': [
        'account_asset_management',
    ],
    'data': [
        'wizards/l10n_be_account_asset_installer.xml',
    ],
    'installable': True,
}
