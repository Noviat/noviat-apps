/** @odoo-module */
/*
    Copyright 2009-2024 Noviat.
    License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
*/

import {BankRecKanbanRenderer} from "@account_accountant/components/bank_reconciliation/kanban";
import {_t} from "@web/core/l10n/translation";
import {patch} from "@web/core/utils/patch";

patch(BankRecKanbanRenderer.prototype, {
    openStatementDialog(statementId) {
        const action = {
            type: "ir.actions.act_window",
            name: _t("Edit Statement"),
            res_model: "account.bank.statement",
            res_id: statementId,
            views: [[false, "form"]],
            target: "new",
            context: {
                dialog_size: "large",
                form_view_ref:
                    "account_bank_statement_advanced.account_bank_statement_view_form",
            },
        };
        const options = {
            onClose: async () => {
                this.env.methods.withNewState(async (newState) => {
                    await this.props.list.model.root.load();
                    await this.env.methods.updateJournalState(newState);
                    newState.__kanbanNotify = true;
                });
            },
        };
        this.action.doAction(action, options);
    },
});
