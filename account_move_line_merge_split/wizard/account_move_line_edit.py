# Copyright 2024 NETKIA S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from dateutil.relativedelta import relativedelta

from odoo import _, exceptions, fields, models


class AccountMoveLineEdit(models.Model):
    _name = "account_move_line_edit"

    division_nr = fields.Integer("Number of Divisions", default=2)
    division_line_ids = fields.One2many(
        "account_move_line_edit_line",
        "config_id",
        string="Division Lines",
        copy=True,
        auto_join=True,
    )
    move_line_id = fields.Many2one("account.move.line", "Move Line")
    move_line_value = fields.Float("Total Move Line Value")
    aggregation_date = fields.Date()

    def generate_lines(self):
        """
        Generates the division lines for splitting a move line.
        Validates the input values and ensures that the selected
        move line can be split.
        """
        if not self.division_nr or self.division_nr <= 1:
            raise exceptions.ValidationError(
                _("You must specify a valid number of divisions.")
            )

        if self.division_line_ids:
            self.division_line_ids.unlink()

        move_lines_ids = self.env.context.get("active_ids", False)
        if len(move_lines_ids) > 1:
            raise exceptions.ValidationError(
                _("To divide move lines, you must select only one.")
            )

        move_line_id = self.env["account.move.line"].search(
            [("id", "in", move_lines_ids)], limit=1
        )
        self.move_line_id = move_line_id.id

        # A move line without a maturity date cannot be divided.
        if not move_line_id.date_maturity:
            raise exceptions.ValidationError(
                _(
                    "Cannot divide the move line '%s' as it does not have a maturity date."
                )
                % move_line_id.name
            )

        split_credit, split_debit, val = 0, 0, 0
        if move_line_id.credit > 0:
            split_credit = move_line_id.credit / self.division_nr
            self.move_line_value = move_line_id.credit
            val = move_line_id.company_id.currency_id.round(split_credit)
        if move_line_id.debit > 0:
            split_debit = move_line_id.debit / self.division_nr
            self.move_line_value = move_line_id.debit
            val = move_line_id.company_id.currency_id.round(split_debit)

        new_due_date = move_line_id.date_maturity
        for _division in range(self.division_nr):
            self.env["account_move_line_edit_line"].create(
                {
                    "config_id": self.id,
                    "name": move_line_id.name,
                    "customer_id": move_line_id.partner_id.id,
                    "amount": val,
                    "due_date": new_due_date,
                }
            )
            new_due_date = new_due_date + relativedelta(months=1)

        # Adjust the first division line for rounding differences
        new_move_line_value = sum(line.amount for line in self.division_line_ids)
        diff = self.move_line_value - new_move_line_value
        self.division_line_ids[0].amount += diff

        return {
            "context": self.env.context,
            "view_type": "form",
            "view_mode": "form",
            "res_model": "account_move_line_edit",
            "res_id": self.id,
            "view_id": self.env.ref(
                "account_move_line_merge_split.account_move_line_split_form"
            ).id,
            "type": "ir.actions.act_window",
            "target": "new",
        }

    def split_move_line(self):
        """
        Splits the selected move line into the generated division lines.
        Ensures the sum of the new lines matches the original move
        line"s value.
        """
        if not self.move_line_id or not self.division_line_ids:
            raise exceptions.ValidationError(
                _("You must generate the division lines first.")
            )

        if self.validate_edit_move_lines(self.move_line_id):
            new_move_line_value = round(
                sum(line.amount for line in self.division_line_ids), 2
            )
            if (
                self.move_line_id.debit > 0
                and not self.move_line_id.debit == new_move_line_value
            ) or (
                self.move_line_id.credit > 0
                and not self.move_line_id.credit == new_move_line_value
            ):
                raise exceptions.ValidationError(
                    _(
                        "The sum of the division lines "
                        "(%(new_move_line_value)s) does not match "
                        "the original move line's value (%(move_line_value)s)."
                    )
                    % {
                        "new_move_line_value": new_move_line_value,
                        "move_line_value": self.move_line_value,
                    }
                )

            new_move_lines = self.env["account.move.line"]
            for line in self.division_line_ids:
                new_move_line = self.env["account.move.line"]
                if self.move_line_id.credit > 0:
                    new_move_line = (
                        self.env["account.move.line"]
                        .with_context(check_move_validity=False)
                        .create(
                            self.get_vals(
                                self.move_line_id, line.amount, 0, line.due_date
                            )
                        )
                    )
                if self.move_line_id.debit > 0:
                    new_move_line = (
                        self.env["account.move.line"]
                        .with_context(check_move_validity=False)
                        .create(
                            self.get_vals(
                                self.move_line_id, 0, line.amount, line.due_date
                            )
                        )
                    )
                new_move_lines += new_move_line

            if len(new_move_lines) == len(self.division_line_ids):
                self.move_line_id.with_context(force_delete=True).unlink()
            else:
                new_move_lines.unlink()
                raise exceptions.ValidationError(
                    _("The new move lines could not be generated correctly.")
                )

        return True

    def merge_move_lines(self):
        """
        Merges the selected move lines into a single move line.
        Validates that the selected lines belong to the same account and move.
        """
        move_lines_ids = self.env.context.get("active_ids", False)
        move_lines = self.env["account.move.line"].search(
            [("id", "in", move_lines_ids)]
        )
        if len(move_lines) == 1:
            raise exceptions.ValidationError(_("You have selected only one move line."))

        if self.validate_edit_move_lines(move_lines):
            merged_credit, merged_debit = 0, 0
            for move_line in move_lines:
                merged_credit += move_line.credit
                merged_debit += move_line.debit

            self.env["account.move.line"].with_context(
                check_move_validity=False
            ).create(
                self.get_vals(
                    move_lines[0],
                    merged_credit,
                    merged_debit,
                    self.aggregation_date,
                )
            )

            move_lines.with_context(force_delete=True).unlink()

    def validate_edit_move_lines(self, move_line_ids):
        """
        Validates the move lines to ensure they can be edited or merged.

        :param move_line_ids: Array of move_line records.
        Ensures all lines belong to the same move and account, and are not reconciled.
        """
        move_id, account_id = False, False
        for move_line_id in move_line_ids:
            if move_id and move_id != move_line_id.move_id.id:
                raise exceptions.ValidationError(
                    _("You have selected move lines from different invoices.")
                )
            elif account_id and account_id != move_line_id.account_id.id:
                raise exceptions.ValidationError(
                    _("You have selected move lines from different accounts.")
                )
            else:
                move_id = move_line_id.move_id.id
                account_id = move_line_id.account_id.id
            if move_line_id.reconciled:
                raise exceptions.ValidationError(
                    _("You are trying to edit a reconciled move line.")
                )
        return True

    def get_vals(self, move_line_id, credit, debit, date):
        """
        Returns the values required to create a new account move line.

        :param move_line_id: The original account.move.line object.
        :param credit: Credit value for the new move line.
        :param debit: Debit value for the new move line.
        :param date: Maturity date for the new move line.
        """
        return {
            "move_id": move_line_id.move_id.id,
            "account_id": move_line_id.account_id.id,
            "journal_id": move_line_id.journal_id.id,
            "partner_id": move_line_id.partner_id.id,
            "date": date,
            "invoice_date": move_line_id.invoice_date,
            "invoice_origin": move_line_id.invoice_origin,
            "name": move_line_id.name,
            "partner_ref": move_line_id.partner_ref,
            "payment_term_id": move_line_id.payment_term_id.id,
            "analytic_distribution": move_line_id.analytic_distribution,
            "credit": credit,
            "debit": debit,
            "balance": debit - credit,
            "amount_residual": debit - credit,
            "date_maturity": date,
            "reconciled": False,
            "full_reconcile_id": False,
            "display_type": move_line_id.display_type,
        }
