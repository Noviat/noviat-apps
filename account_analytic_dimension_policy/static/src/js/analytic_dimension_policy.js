/*
  Copyright 2009-2022 Noviat
  License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
*/

odoo.define("account_analytic_dimensions_policy.analytic_dimensions_policy", function(
    require
) {
    "use strict";

    var ReconciliationModel = require("account.ReconciliationModel");
    var ReconciliationRenderer = require("account.ReconciliationRenderer");
    var relational_fields = require("web.relational_fields");
    var basic_fields = require("web.basic_fields");
    var session = require("web.session");

    ReconciliationModel.StatementModel.include({
        init: function() {
            this._super.apply(this, arguments);
            this.quickCreateFieldsStandard = [
                "account_id",
                "amount",
                "analytic_account_id",
                "label",
                "tax_ids",
                "force_tax_included",
                "analytic_tag_ids",
                "to_check",
            ];
            this._SetAnalyticDimensionPolicy();
        },

        _SetAnalyticDimensionPolicy: function() {
            var self = this;
            return this._rpc({
                model: "account.account",
                method: "search_read",
                fields: ["id", "analytic_dimensions"],
                domain: [
                    ["analytic_dimension_policy", "in", ["always", "posted"]],
                    ["deprecated", "=", false],
                    ["company_id", "=", session.company_id],
                ],
            }).then(function(accounts) {
                self.AnalyticDimensionPolicyRequiredAccounts = accounts;
                self.AnalyticDimensions = [];
                self.NewAnalyticDimensions = [];
                self.NewAnalyticDimensionsFields = [];
                return self
                    ._rpc({
                        model: "account.move.line",
                        method: "get_analytic_dimension_fields",
                        args: [session.company_id],
                    })
                    .then(function(dimensions) {
                        self.AnalyticDimensions = _.pluck(dimensions, "name");
                        _.each(dimensions, function(field) {
                            if (field.name !== "partner_id") {
                                if (!self.quickCreateFields.includes(field.name)) {
                                    self.quickCreateFields.push(field.name);
                                }
                                if (
                                    !self.quickCreateFieldsStandard.includes(field.name)
                                ) {
                                    self.NewAnalyticDimensions.push(field.name);
                                    self.NewAnalyticDimensionsFields.push(field);
                                }
                            }
                        });
                    });
            });
        },

        _formatQuickCreate: function(line, values) {
            var prop = this._super(line, values);
            _.each(this.NewAnalyticDimensions, function(field) {
                prop[field] = false;
            });
            return prop;
        },

        makeRecord: function(model, fields, fieldInfo) {
            if (
                model === "account.bank.statement.line" &&
                fields.some(field => field.name === "amount")
            ) {
                _.each(this.NewAnalyticDimensionsFields, function(field) {
                    fields.push(field);
                });
                _.extend(
                    fieldInfo,
                    _.pluck(this.NewAnalyticDimensionsFields, "string")
                );
            }
            return this._super(model, fields, fieldInfo);
        },

        _formatToProcessReconciliation: function(line, prop) {
            var result = this._super(line, prop);
            _.each(this.NewAnalyticDimensions, function(field) {
                if (prop[field]) {
                    result[field] = prop[field].id ? prop[field].id : prop[field];
                }
            });
            return result;
        },

        _computeLine: function(line) {
            var self = this;
            return this._super(line).then(function() {
                var props = _.reject(line.reconciliation_proposition, "invalid");
                if (line.balance.type >= 0) {
                    _.each(props, function(prop) {
                        if (prop.account_id) {
                            self._setBalanceTypeForAnalyticDimensions(line, prop);
                        }
                        if (line.balance.type === -1) {
                            return false;
                        }
                    });
                }
            });
        },

        _setBalanceTypeForAnalyticDimensions: function(line, prop) {
            var policy = this.AnalyticDimensionPolicyRequiredAccounts.find(
                item => item.id === prop.account_id.id
            );
            var required_dims = (policy && policy.analytic_dimensions.split(",")) || [];
            _.each(required_dims, function(dim) {
                if (
                    (dim === "partner_id" && !line.st_line.partner_id) ||
                    (dim !== "partner_id" && !prop[dim])
                ) {
                    line.balance.type = -1;
                    return false;
                }
            });
        },
    });

    ReconciliationRenderer.LineRenderer.include({
        _renderCreate: function(state) {
            var self = this;
            return Promise.resolve(this._super(state)).then(function() {
                var record = self.model.get(self.handleCreateRecord);
                _.each(self.model.NewAnalyticDimensionsFields, function(field) {
                    if (field.type === "many2one") {
                        self.fields[
                            field.name
                        ] = new relational_fields.FieldMany2One(
                            self,
                            field.name,
                            record,
                            {mode: "edit", attrs: {can_create: false}}
                        );
                    } else if (field.type === "many2many") {
                        self.fields[
                            field.name
                        ] = new relational_fields.FieldMany2ManyTags(
                            self,
                            field.name,
                            record,
                            {mode: "edit", attrs: {can_create: false}}
                        );
                    } else if (field.type === "selection") {
                        self.fields[
                            field.name
                        ] = new relational_fields.FieldSelection(
                            self,
                            field.name,
                            record,
                            {mode: "edit"}
                        );
                    } else {
                        self.fields[field.name] = new basic_fields.FieldChar(
                            self,
                            field.name,
                            record,
                            {mode: "edit"}
                        );
                    }
                    self.fields[field.name].appendTo(
                        self.$el.find(".create_" + field.name + " .o_td_field")
                    );
                });
            });
        },

        _onFieldChanged: function(event) {
            this._super(event);
            var self = this;
            var fieldName = event.target.name;
            if (fieldName === "account_id") {
                var account_id = event.data.changes.account_id.id;
                this._SetAnalyticDimensionModifiers(account_id);
            } else if (fieldName === "partner_id") {
                var required_accounts = _.filter(
                    self.model.AnalyticDimensionPolicyRequiredAccounts,
                    function(account) {
                        return account.analytic_dimensions
                            .split(",")
                            .includes("partner_id");
                    }
                );
                var required_account_ids = _.pluck(required_accounts, "id");
                var props = [];
                _.each(this.model.lines, function(line) {
                    var line_props = _.filter(line.reconciliation_proposition, function(
                        prop
                    ) {
                        return (
                            !prop.invalid &&
                            required_account_ids.includes(prop.account_id.id)
                        );
                    });
                    props.concat(line_props);
                });
                if (props.length) {
                    this._SetAnalyticDimensionModifiers(props[0].account_id.id);
                }
            }
        },

        update: function(state) {
            this._super(state);
            var prop =
                Boolean(state.reconciliation_proposition.length) &&
                state.reconciliation_proposition[0];
            if (prop && prop.account_id) {
                this._SetAnalyticDimensionModifiers(prop.account_id.id);
            }
        },

        _SetAnalyticDimensionModifiers: function(account_id) {
            var self = this;
            var policy = this.model.AnalyticDimensionPolicyRequiredAccounts.find(
                item => item.id === account_id
            );
            var required_dimensions =
                (policy && policy.analytic_dimensions.split(",")) || [];
            _.each(this.model.AnalyticDimensions, function(dim) {
                if (self.fields[dim]) {
                    if (policy) {
                        if (required_dimensions.includes(dim)) {
                            self.fields[dim].$el.addClass("o_required_modifier");
                        } else {
                            self.fields[dim].$el.removeClass("o_required_modifier");
                        }
                    } else {
                        self.fields[dim].$el.removeClass("o_required_modifier");
                    }
                }
            });
        },
    });
});
