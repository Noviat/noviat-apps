/*
 Copyright 2009-2022 Noviat.
 License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
*/
odoo.define("web_tree_date_search.ir_parameters", function (require) {
    "use strict";

    var rpc = require("web.rpc");

    return rpc.query({
        model: "ir.config_parameter",
        method: "get_web_tree_date_search_parameters",
    });
});
