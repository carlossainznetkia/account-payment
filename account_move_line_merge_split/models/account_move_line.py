# Copyright 2024 NETKIA S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def action_split_move_lines(self):
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "account_move_line_merge_split.account_move_line_split_wizard_action"
        )
        ctx = self.env.context.copy()
        ctx.update({"active_ids": self.ids, "active_model": "account_move_line_edit"})
        action["context"] = ctx
        return action

    def action_merge_move_lines(self):
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "account_move_line_merge_split.account_move_line_merge_wizard_action"
        )
        ctx = self.env.context.copy()
        ctx.update({"active_ids": self.ids, "active_model": "account_move_line_edit"})
        action["context"] = ctx
        return action
