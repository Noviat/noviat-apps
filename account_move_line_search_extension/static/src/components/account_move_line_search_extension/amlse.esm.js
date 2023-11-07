/** @odoo-module */
/*
    Copyright 2009-2023 Noviat.
    License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
*/

import {onMounted, onRendered} from "@odoo/owl";
import {ListRenderer} from "@web/views/list/list_renderer";
import {listView} from "@web/views/list/list_view";
import {registry} from "@web/core/registry";
import rpc from "web.rpc";

export class accountMoveLineSearchExtensionListRenderer extends ListRenderer {
    setup() {
        var self = this;
        self.amlse_domain = [];
        super.setup();
        onRendered(() => {
            var dts = this.amlse_domain;
            if (dts && dts.length > 0) {
                var is_in = false;
                var pdomains = this.props.list.domain;
                for (var i = 0; i < pdomains.length; i++) {
                    for (var j = 0; j < dts.length; j++) {
                        if (pdomains[i].toString() === dts[j].toString()) {
                            is_in = true;
                            break;
                        }
                    }
                    if (is_in) {
                        break;
                    }
                }
                if (!is_in) {
                    var list = $(".oe_amlse_tr_input input, select");
                    for (var k = 0; k < list.length; k++) {
                        list[k].value = null;
                    }
                    self.amlse_domain = [];
                    self._apply_custom_search_domain(self.amlse_domain);
                    self.is_custom_buttons_already_rendered = false;
                }
            }
        });
        onMounted(() => {
            if (this.is_custom_buttons_already_rendered !== true) {
                rpc.query({
                    model: "account.journal",
                    method: "search_read",
                    fields: ["name"],
                    kwargs: {
                        // Context: self.props.context,
                        context: self.userService.context,
                    },
                }).then(function (result) {
                    self.journals = result;
                    var oesj = $("select.oe_account_select_journal");
                    oesj.children().remove().end();
                    oesj.append(new Option("", ""));
                    for (var a = 0; a < self.journals.length; a++) {
                        var o = new Option(self.journals[a].name, self.journals[a].id);
                        oesj.append(o);
                    }
                    self.is_custom_buttons_already_rendered = true;
                });
            }
        });
    }

    _onchange_data(ev) {
        var search_item = ev.srcElement.classList[0];
        var v = ev.srcElement.value;
        if (search_item === "oe_account_select_product") {
            this.current_product = v;
        }
        if (search_item === "oe_account_select_account") {
            this.current_account = v;
        }
        if (search_item === "oe_account_select_partner") {
            this.current_partner = v;
        }
        if (search_item === "oe_account_select_journal") {
            this.current_journal = parseInt(v, 10);
        }
        if (search_item === "oe_account_select_period") {
            this.current_period = v;
        }
        if (search_item === "oe_account_select_reconcile") {
            this.current_reconcile = v;
        }
        if (search_item === "oe_account_select_amount") {
            this.current_amount = v;
        }
        if (search_item === "oe_account_select_taxes") {
            this.current_taxes = v;
        }
        if (search_item === "oe_account_select_tags") {
            this.current_tags = v;
        }
        this.amlse_domain = this._build_custom_search_domain();
        this._apply_custom_search_domain(this.amlse_domain);
    }

    _init_values() {
        this.current_product = null;
        this.current_account = null;
        this.current_partner = null;
        this.current_journal = null;
        this.current_period = null;
        this.current_reconcile = null;
        this.current_amount = null;
        this.current_taxes = null;
        this.current_tags = null;
    }

    _apply_custom_search_domain(domain) {
        var special_char = "🌟";
        if (this.amlse_domain === undefined || this.amlse_domain.length === 0) {
            this._init_values();
            if (
                this.env.searchModel.domainParts.state &&
                this.env.searchModel.domainParts.state.facetLabel === special_char
            ) {
                this.env.searchModel.deactivateGroup(
                    this.env.searchModel.domainParts.state.groupId
                );
            }
        } else {
            this.env.searchModel.setDomainParts({
                state: {
                    domain: domain,
                    facetLabel: special_char,
                },
            });
        }
    }
    _build_custom_search_domain() {
        var domain = [];
        if (this.current_product)
            domain.push(
                "|",
                ["product_id.name", "ilike", this.current_product],
                ["product_id.default_code", "ilike", this.current_product]
            );
        if (this.current_account)
            domain.push([
                "account_id.code",
                "=ilike",
                this.current_account.concat("%"),
            ]);
        if (this.current_partner)
            domain.push(["partner_id.name", "ilike", this.current_partner]);
        if (this.current_journal)
            domain.push(["journal_id", "=", this.current_journal]);
        if (this.current_period)
            domain.push(["period_search", "=", this.current_period]);
        if (this.current_reconcile)
            domain.push(["full_reconcile_id.name", "=ilike", this.current_reconcile]);
        if (this.current_amount)
            domain.push(["amount_search", "=", this.current_amount]);
        if (this.current_taxes) domain.push(["tax_ids", "ilike", this.current_taxes]);
        if (this.current_tags) domain.push(["tax_tag_ids", "ilike", this.current_tags]);
        return domain;
    }
}
accountMoveLineSearchExtensionListRenderer.template = "AccountMoveLineSearchExtension";

export const accountMoveLineSearchExtensionListView = {
    ...listView,
    Renderer: accountMoveLineSearchExtensionListRenderer,
};

registry
    .category("views")
    .add(
        "account_move_line_search_extension_list_view",
        accountMoveLineSearchExtensionListView
    );
