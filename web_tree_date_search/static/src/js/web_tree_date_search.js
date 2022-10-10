/*
 Copyright 2009-2022 Noviat.
 License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
*/

odoo.define("web_tree_date_search", function (require) {
    "use strict";

    var core = require("web.core");
    var QWeb = core.qweb;
    var ListController = require("web.ListController");
    var datepicker = require("web.datepicker");
    var ir_parameters = require("web_tree_date_search.ir_parameters");

    ListController.include({
        init: function () {
            var self = this;
            this._super.apply(this, arguments);
            this.date_search_domain = [];
            var parameter_applicability =
                ir_parameters["web_tree_date_search.applicability"];
            if (["all", "selective"].includes(parameter_applicability)) {
                var dateFilterBool = false;
                var dateFilterArray = [];
                if (
                    "context" in self.initialState &&
                    "dates_filter" in self.initialState.context
                ) {
                    if (Array.isArray(self.initialState.context.dates_filter)) {
                        if (self.initialState.context.dates_filter.length > 0) {
                            dateFilterBool = true;
                            dateFilterArray = self.initialState.context.dates_filter;
                        }
                    } else if (
                        typeof self.initialState.context.dates_filter === "boolean"
                    ) {
                        dateFilterBool = self.initialState.context.dates_filter;
                    }
                } else if (parameter_applicability === "all") {
                    dateFilterBool = true;
                }
                var dateFilters = [];
                var fields = [];
                if (dateFilterBool) {
                    if (dateFilterArray.length > 0) {
                        dateFilters = self._get_date_filter_list(self, dateFilterArray);
                    } else {
                        fields = Object.keys(self.initialState.fieldsInfo.list);
                        dateFilters = self._get_date_filter_list(self, fields);
                    }
                    this.dates_filter = dateFilters;
                }
            }
        },

        start: function () {
            this._super.apply(this, arguments);
            var self = this;
            if ("dates_filter" in self) {
                var $content = $(
                    QWeb.render("web_tree_date_search_toolbar", {
                        dateFilters: self.dates_filter,
                    })
                );
                // self.$(".o_content").prepend($content);
                self.$(".o_content").before($content);
                _.each(self.dates_filter, function (dateFilter) {
                    self._get_date_picker(dateFilter, "from", $content);
                    self._get_date_picker(dateFilter, "to", $content);
                });
            }
        },

        _update: function (state, params) {
            /* Save initial searchbar params for use in reload */
            if (!this.reload_params) {
                this.reload_params = _.pick(state, [
                    "offset",
                    "groupsOffset",
                    "context",
                    "domain",
                    "orderedBy",
                    "groupBy",
                    "selectedRecords",
                ]);
            }
            return this._super(state, params);
        },

        reload: function (params) {
            var self = this;
            if (params && params.domain) {
                this.reload_params = params;
                params.domain = this.date_search_domain.concat(params.domain);
            }
            return this._super.apply(this, arguments).then(function () {
                /* Restore search bar domain since the _super will set it to the concatenated domain */
                if (params && params.domain) {
                    self.reload_params.domain = self.reload_params.domain.slice(
                        self.date_search_domain.length
                    );
                }
            });
        },

        _get_date_picker: function (dateFilter, target, $content) {
            var options = {
                // Set the options for the datetimepickers
                locale: moment.locale(),
            };
            var datePicker = null;
            if (dateFilter.type === "date") {
                datePicker = new datepicker.DateWidget(this, options);
            } else {
                datePicker = new datepicker.DateTimeWidget(this, options);
            }
            var element = $content.find(
                "div.oe_date_filter_" + target + "_" + dateFilter.name
            );
            datePicker.on("datetime_changed", this, function () {
                this._changeValue(datePicker.getValue(), dateFilter, target);
            });
            datePicker.appendTo(element).then(function () {
                datePicker.$input.attr(
                    "placeholder",
                    target.charAt(0).toUpperCase() + target.slice(1)
                );
            });
            return datePicker;
        },

        _changeValue: function (moment, dateFilter, target) {
            var date_search_domain = this.date_search_domain;
            var new_date_search_domain = [];
            if (date_search_domain) {
                _.each(date_search_domain, function (domain_array) {
                    if (
                        domain_array[0] !== dateFilter.name ||
                        (domain_array[0] === dateFilter.name &&
                            ((target === "to" && domain_array[1] !== "<=") ||
                                (target === "from" && domain_array[1] !== ">=")))
                    ) {
                        new_date_search_domain.push(domain_array);
                    }
                });
            }
            if (moment !== false) {
                if (target === "to") {
                    new_date_search_domain.push([
                        dateFilter.name,
                        "<=",
                        moment.format("YYYY-MM-DD"),
                    ]);
                } else {
                    new_date_search_domain.push([
                        dateFilter.name,
                        ">=",
                        moment.format("YYYY-MM-DD"),
                    ]);
                }
            }
            this.date_search_domain = new_date_search_domain;
            this.reload(this.reload_params);
        },

        _get_date_filter_list: function (self, fields) {
            var dateFilters = [];
            fields.forEach(function (field_name) {
                if (
                    typeof self.initialState.fields[field_name] != 'undefined' &&
                    ["date", "datetime"].includes(
                        self.initialState.fields[field_name].type
                    ) &&
                    (self.initialState.fieldsInfo.list[field_name].invisible !== "1" ||
                        !self.initialState.fieldsInfo.list[field_name].invisible) &&
                    self.initialState.fields[field_name].searchable === true
                ) {
                    dateFilters.push({
                        type: self.initialState.fields[field_name].type,
                        display_name: self.initialState.fields[field_name].string,
                        name: field_name,
                    });
                }
            });
            return dateFilters;
        },
    });
});
