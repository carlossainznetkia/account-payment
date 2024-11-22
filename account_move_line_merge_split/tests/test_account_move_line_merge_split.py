# Copyright 2024 NETKIA S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from datetime import datetime

from dateutil.relativedelta import relativedelta

from odoo import exceptions, fields
from odoo.tests import common


class TestAmlSplitMoveLines(common.TransactionCase):
    def setUp(self):
        super(TestAmlSplitMoveLines, self).setUp()
        self.env = self.env(context=dict(self.env.context, tracking_disable=True))
        self.AccountMove = self.env["account.move"]
        self.company = self.env.ref("base.main_company")
        self.partner = self.env.ref("base.partner_demo")
        self.product = self.env.ref("product.product_delivery_02")
        self.account = self.env["account.account"].create(
            {
                "code": "test_cash_pay_invoice",
                "company_id": self.company.id,
                "name": "Test",
                "user_type_id": self.env.ref("account.data_account_type_revenue").id,
                "reconcile": True,
            }
        )
        self.account2 = self.env["account.account"].create(
            {
                "code": "test_cash_pay_invoice_2",
                "company_id": self.company.id,
                "name": "Test_2",
                "user_type_id": self.env.ref("account.data_account_type_revenue").id,
                "reconcile": True,
            }
        )
        self.invoice_out = self.AccountMove.create(
            {
                "company_id": self.company.id,
                "partner_id": self.partner.id,
                "date": "2016-03-12",
                "move_type": "out_invoice",
                "invoice_line_ids": [
                    (
                        0,
                        False,
                        {
                            "product_id": self.product.id,
                            "account_id": self.account.id,
                            "name": "Producto de prueba",
                            "quantity": 1.0,
                            "price_unit": 100.0,
                            "date_maturity": datetime.today(),
                        },
                    ),
                    (
                        0,
                        False,
                        {
                            "product_id": self.product.id,
                            "account_id": self.account.id,
                            "name": "Producto de prueba",
                            "quantity": 1.0,
                            "price_unit": 100.0,
                            "date_maturity": datetime.today(),
                        },
                    ),
                ],
            }
        )
        self.invoice_out._onchange_invoice_line_ids()
        self.invoice_out.action_post()
        self.invoice_out.name = "2999/99999"

        self.invoice_in = self.AccountMove.create(
            {
                "company_id": self.company.id,
                "partner_id": self.partner.id,
                "date": "2016-03-12",
                "invoice_date": "2016-03-12",
                "move_type": "in_invoice",
                "invoice_line_ids": [
                    (
                        0,
                        False,
                        {
                            "product_id": self.product.id,
                            "account_id": self.account.id,
                            "name": "Producto de prueba",
                            "quantity": 1.0,
                            "price_unit": 100.0,
                            "date_maturity": datetime.today(),
                        },
                    ),
                    (
                        0,
                        False,
                        {
                            "product_id": self.product.id,
                            "account_id": self.account.id,
                            "name": "Producto de prueba",
                            "quantity": 1.0,
                            "price_unit": 100.0,
                            "date_maturity": datetime.today(),
                        },
                    ),
                ],
            }
        )
        self.invoice_in._onchange_invoice_line_ids()
        self.invoice_in.action_post()
        self.invoice_in.name = "3999/99999"

        self.journal = (
            self.env["account.journal"]
            .search(
                [("company_id", "=", self.company.id), ("type", "=", "cash")], limit=1
            )
            .ensure_one()
        )

        self.line_out = self.invoice_out.line_ids[0]
        self.line_out2 = self.invoice_out.line_ids[1]
        self.line_in = self.invoice_in.line_ids[0]
        self.line_in2 = self.invoice_in.line_ids[1]

        self.another_line_out_move = self.AccountMove.create(
            {
                "journal_id": self.journal.id,
                "date": fields.Date.today(),
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Another Test Line Debit",
                            "account_id": self.account.id,
                            "debit": 50.0,
                            "credit": 0.0,
                            "date_maturity": datetime.today() + relativedelta(months=1),
                            "partner_id": self.partner.id,
                            "company_id": self.company.id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Another Test Line Credit",
                            "account_id": self.account.id,
                            "debit": 0.0,
                            "credit": 50.0,
                            "date_maturity": datetime.today() + relativedelta(months=1),
                            "partner_id": self.partner.id,
                            "company_id": self.company.id,
                        },
                    ),
                ],
            }
        )
        self.another_line_out_move.action_post()

        self.another_line_out = self.another_line_out_move.line_ids.filtered(
            lambda a: a.debit == 0.0 and a.credit == 50.0
        )

    def test_action_split_move_lines(self):
        action = self.line_out.action_split_move_lines()
        self.assertEqual(action["res_model"], "account_move_line_edit")

    def test_action_merge_move_lines(self):
        action = self.line_out.action_merge_move_lines()
        self.assertEqual(action["res_model"], "account_move_line_edit")

    def test_generate_lines(self):
        wizard = self.env["account_move_line_edit"].create(
            {
                "division_nr": 3,
            }
        )
        wizard.with_context(active_ids=[self.line_out.id]).generate_lines()
        self.assertEqual(len(wizard.division_line_ids), 3)
        self.assertAlmostEqual(
            sum(linea.amount for linea in wizard.division_line_ids), 100
        )

    def test_generate_lines_invalid_division_nr(self):
        with self.assertRaises(exceptions.ValidationError):
            wizard = self.env["account_move_line_edit"].create(
                {
                    "division_nr": 0,  # Valor inválido
                }
            )
            wizard.with_context(active_ids=[self.line_out.id]).generate_lines()

    def test_generate_lines_invalid_division_nr_equal_1(self):
        with self.assertRaises(exceptions.ValidationError):
            wizard = self.env["account_move_line_edit"].create(
                {
                    "division_nr": 1,  # Valor inválido
                }
            )
            wizard.with_context(active_ids=[self.line_out.id]).generate_lines()

    def test_generate_lines_multiple_move_lines(self):
        with self.assertRaises(exceptions.ValidationError):
            wizard = self.env["account_move_line_edit"].create(
                {
                    "division_nr": 3,
                }
            )
            wizard.with_context(
                active_ids=[self.line_out.id, self.another_line_out.id]
            ).generate_lines()

    def test_generate_lines_no_maturity_date(self):
        move = self.env["account.move"].create(
            {
                "journal_id": self.journal.id,
                "date": fields.Date.today(),
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Test Move Line",
                            "account_id": self.account.id,
                            "debit": 100,
                            "credit": 0,
                            "date_maturity": False,  # Sin fecha de vencimiento
                            "partner_id": self.partner.id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Balancing Line",
                            "account_id": self.account.id,
                            "debit": 0,
                            "credit": 100,
                            "partner_id": self.partner.id,
                        },
                    ),
                ],
            }
        )

        move_line_id = move.line_ids.filtered(lambda line: line.debit > 0)

        wizard = self.env["account_move_line_edit"].create(
            {
                "division_nr": 3,
            }
        )

        with self.assertRaises(exceptions.ValidationError):
            wizard.with_context(active_ids=[move_line_id.id]).generate_lines()

    def test_generate_lines_zero_credit_debit(self):
        move_line_id = self.env["account.move.line"].create(
            {
                "name": "Test Move Line",
                "move_id": self.invoice_out.id,
                "account_id": self.account.id,
                "journal_id": self.journal.id,
                "debit": 0,
                "credit": 0,
                "date_maturity": "2024-01-01",
                "partner_id": self.invoice_out.partner_id.id,
                "company_id": self.company.id,
            }
        )

        wizard = self.env["account_move_line_edit"].create(
            {
                "division_nr": 3,
            }
        )
        wizard.with_context(active_ids=[move_line_id.id]).generate_lines()

        self.assertEqual(len(wizard.division_line_ids), 3)
        self.assertAlmostEqual(
            sum(linea.amount for linea in wizard.division_line_ids), 0
        )

    def test_merge_move_lines(self):
        # Move for tests
        move = self.env["account.move"].create(
            {
                "journal_id": self.journal.id,
                "date": fields.Date.today(),
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Test Move Line 1",
                            "account_id": self.account.id,
                            "debit": 50,
                            "credit": 0,
                            "date_maturity": fields.Date.today(),
                            "partner_id": self.partner.id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Test Move Line 2",
                            "account_id": self.account.id,
                            "debit": 50,
                            "credit": 0,
                            "date_maturity": fields.Date.today(),
                            "partner_id": self.partner.id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Test Move Line 3",
                            "account_id": self.account2.id,  # Different account to test it
                            "debit": 50,
                            "credit": 0,
                            "date_maturity": fields.Date.today(),
                            "partner_id": self.partner.id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Balancing Line 1",
                            "account_id": self.account.id,
                            "debit": 0,
                            "credit": 150,
                            "partner_id": self.partner.id,
                        },
                    ),
                ],
            }
        )

        # Different move to test it
        move_dif = self.env["account.move"].create(
            {
                "journal_id": self.journal.id,
                "date": fields.Date.today(),
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Test Move Line 1",
                            "account_id": self.account2.id,
                            "debit": 50,
                            "credit": 0,
                            "date_maturity": fields.Date.today(),
                            "partner_id": self.partner.id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Balancing Line 1",
                            "account_id": self.account2.id,
                            "debit": 0,
                            "credit": 50,
                            "partner_id": self.partner.id,
                        },
                    ),
                ],
            }
        )

        move_line1 = move.line_ids[0]
        move_line2 = move.line_ids[1]
        move_line1_dif = move.line_ids[2]  # Different account
        move_line3 = move.line_ids[3]
        move_line2_dif = move_dif.line_ids[0]  # Different move

        wizard = self.env["account_move_line_edit"].create(
            {
                "aggregation_date": fields.Date.today(),
            }
        )

        # Test reconciled line merging
        move_line1.write(
            {
                "reconciled": True,
            }
        )
        with self.assertRaises(exceptions.ValidationError):
            wizard.validate_edit_move_lines([move_line1])
        move_line1.write(
            {
                "reconciled": False,
            }
        )

        # Test different account lines merging
        with self.assertRaises(exceptions.ValidationError):
            wizard.with_context(
                active_ids=[move_line1.id, move_line1_dif.id]
            ).merge_move_lines()

        # Test different move lines merging
        with self.assertRaises(exceptions.ValidationError):
            wizard.with_context(
                active_ids=[move_line2.id, move_line2_dif.id]
            ).merge_move_lines()

        # Test just one move line merging
        with self.assertRaises(exceptions.ValidationError):
            wizard.with_context(active_ids=[move_line1.id]).merge_move_lines()

        # Test good merging
        wizard.with_context(
            active_ids=[move_line1.id, move_line2.id]
        ).merge_move_lines()
        merged_move_line = self.env["account.move.line"].search(
            [
                (
                    "id",
                    "not in",
                    [move_line1.id, move_line2.id, move_line1_dif.id, move_line3.id],
                ),
                ("move_id", "in", [move.id]),
            ]
        )
        self.assertEqual(len(merged_move_line), 1)
        self.assertEqual(merged_move_line.debit, 100)
        self.assertEqual(merged_move_line.credit, 0)

    def test_split_move_line(self):
        wizard = self.env["account_move_line_edit"].create({})

        # Test error if no division_nr set
        with self.assertRaises(exceptions.ValidationError):
            wizard.split_move_line()

        wizard.write(
            {
                "division_nr": 3,
            }
        )

        # Test splitting move line with credit line
        wizard.with_context(active_ids=[self.line_out.id]).generate_lines()
        wizard.split_move_line()
        self.assertEqual(len(wizard.division_line_ids), 3)

        # Test existing division_line_ids deleting
        with self.assertRaises(exceptions.ValidationError):
            wizard.split_move_line()

        # Test wrong amount in lines
        wizard.with_context(active_ids=[self.line_out2.id]).generate_lines()
        d_lines = wizard.division_line_ids
        d_lines[0].amount = 0
        wizard.write(
            {
                "division_line_ids": d_lines,
            }
        )
        with self.assertRaises(exceptions.ValidationError):
            wizard.split_move_line()

        # Test splitting move line with debit line
        wizard.with_context(active_ids=[self.line_in.id]).generate_lines()
        wizard.split_move_line()
        self.assertEqual(len(wizard.division_line_ids), 3)

        # Test wrong amount in lines
        wizard.with_context(active_ids=[self.line_in2.id]).generate_lines()
        d_lines = wizard.division_line_ids
        d_lines[0].amount = 0
        wizard.write(
            {
                "division_line_ids": d_lines,
            }
        )
        with self.assertRaises(exceptions.ValidationError):
            wizard.split_move_line()
