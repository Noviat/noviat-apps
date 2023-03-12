# Copyright 2009-2023 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Underline text in tree/list views",
    "version": "15.0.1.0.0",
    "license": "AGPL-3",
    "author": "Noviat",
    "website": "https://www.noviat.com/",
    "category": "Web",
    "depends": ["web"],
    "summary": "Module that allows to add a new attribute in tree/list views "
    "that underlines your text with conditions (exactly like decoration-bf "
    "for bold)",
    "data": [],
    "assets": {
        "web.assets_backend": [
            "/web_tree_decoration_underline/static/src/scss/**/*",
            "/web_tree_decoration_underline/static/src/js/**/*",
        ],
    },
    "installable": True,
}
