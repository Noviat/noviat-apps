/* Copyright 2018-2023 Noviat (www.noviat.com) */

const DECORATIONS = [
    "decoration-bf",
    "decoration-it",
    "decoration-uf",
    "decoration-danger",
    "decoration-info",
    "decoration-muted",
    "decoration-primary",
    "decoration-success",
    "decoration-warning",
];

odoo.define("web_tree_decoration_underline.ListRenderer", function (require) {
    "use strict";

    var ListRenderer = require("web.ListRenderer");
    var py = window.py;

    ListRenderer.include({
        _extractDecorationAttrs: function (node) {
            const decorations = this._super.apply(this, arguments);
            for (const [key, expr] of Object.entries(node.attrs)) {
                if (DECORATIONS.includes(key)) {
                    if (key === "decoration-uf") {
                        console.log("DECORATION UF");
                        decorations["text-underline"] = py.parse(py.tokenize(expr));
                    }
                }
            }
            return decorations;
        },
    });
});
