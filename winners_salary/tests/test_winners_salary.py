# pyrefly: ignore [missing-import]
from odoo.tests.common import TransactionCase
# pyrefly: ignore [missing-import]
from odoo.exceptions import AccessError, UserError
from odoo import fields


class TestWinnersSalary(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # ── 1. Create Branches ──
        cls.branch_algiers = cls.env["winners.branch"].create({
            "name": "Branche Alger",
            "is_active": True,
        })
        cls.branch_oran = cls.env["winners.branch"].create({
            "name": "Branche Oran",
            "is_active": True,
        })

        # ── 2. Create Users/Roles ──
        # Super Admin user (Super Admin role is managed via res.users inherit in winners_auth)
        cls.user_super_admin = cls.env["res.users"].create({
            "name": "Super Admin Test",
            "login": "super_admin_test@winners.com",
            "email": "super_admin_test@winners.com",
            "winners_role": "super_admin",
            "branch_id": cls.branch_algiers.id,
        })

        # Director for Algiers branch
        cls.user_director_algiers = cls.env["res.users"].create({
            "name": "Directeur Alger",
            "login": "dir_algiers@winners.com",
            "email": "dir_algiers@winners.com",
            "winners_role": "director",
            "branch_id": cls.branch_algiers.id,
        })

        # Director for Oran branch
        cls.user_director_oran = cls.env["res.users"].create({
            "name": "Directeur Oran",
            "login": "dir_oran@winners.com",
            "email": "dir_oran@winners.com",
            "winners_role": "director",
            "branch_id": cls.branch_oran.id,
        })

        # Cashier user
        cls.user_cashier = cls.env["res.users"].create({
            "name": "Caissier Test",
            "login": "cashier_test@winners.com",
            "email": "cashier_test@winners.com",
            "winners_role": "cashier",
            "branch_id": cls.branch_algiers.id,
        })

        # ── 3. Create Teachers ──
        cls.teacher_algiers = cls.env["winners.teacher"].create({
            "name": "Ahmed Mourad",
            "phone": "0555123456",
            "specialty": "arabic",
            "branch_id": cls.branch_algiers.id,
            "base_salary": 45000.0,
        })
        cls.teacher_oran = cls.env["winners.teacher"].create({
            "name": "Mohamed Ben Ali",
            "phone": "0666123456",
            "specialty": "math",
            "branch_id": cls.branch_oran.id,
            "base_salary": 50000.0,
        })

    def test_01_salary_computations(self):
        """Test salary calculations: base + overtime + bonus - deductions = net."""
        # Create salary slip as Super Admin
        salary_slip = self.env["winners.salary"].with_user(self.user_super_admin).create({
            "teacher_id": self.teacher_algiers.id,
            "period_start": "2026-07-01",
            "period_end": "2026-07-31",
            "base_salary": 45000.0,
            "overtime_hours": 10.0,
            "overtime_rate": 500.0, # 10 * 500 = 5000
            "bonus": 2000.0,
            "bonus_justification": "Performance prime",
            "other_deductions": 1000.0,
            "deductions_justification": "Retard excessif",
        })

        # Verify net salary: 45000 + 5000 + 2000 - 1000 = 51000
        self.assertEqual(salary_slip.net_salary, 51000.0, "Le calcul du salaire net est incorrect.")

    def test_02_unauthorized_user_access(self):
        """Test that a cashier (unauthorized) cannot create or modify a salary slip."""
        # Cashier tries to create a salary slip -> AccessError expected
        with self.assertRaises(AccessError):
            self.env["winners.salary"].with_user(self.user_cashier).create({
                "teacher_id": self.teacher_algiers.id,
                "period_start": "2026-07-01",
                "period_end": "2026-07-31",
                "base_salary": 45000.0,
            })

        # Let's create a slip as Super Admin first
        salary_slip = self.env["winners.salary"].with_user(self.user_super_admin).create({
            "teacher_id": self.teacher_algiers.id,
            "period_start": "2026-07-01",
            "period_end": "2026-07-31",
            "base_salary": 45000.0,
        })

        # Cashier tries to modify the salary slip -> AccessError expected
        with self.assertRaises(AccessError):
            salary_slip.with_user(self.user_cashier).write({
                "base_salary": 50000.0,
            })

    def test_03_director_branch_rules(self):
        """Test that a Director can only access/modify salary slips of their own branch."""
        # Director Algiers creates salary slip for Algiers teacher -> OK
        salary_slip_algiers = self.env["winners.salary"].with_user(self.user_director_algiers).create({
            "teacher_id": self.teacher_algiers.id,
            "period_start": "2026-07-01",
            "period_end": "2026-07-31",
            "base_salary": 45000.0,
        })
        self.assertTrue(salary_slip_algiers.id)

        # Director Algiers tries to create a slip for Oran teacher -> AccessError expected (due to branch_id mismatch)
        with self.assertRaises(AccessError):
            self.env["winners.salary"].with_user(self.user_director_algiers).create({
                "teacher_id": self.teacher_oran.id,
                "period_start": "2026-07-01",
                "period_end": "2026-07-31",
                "base_salary": 50000.0,
            })

        # Director Oran tries to read Algiers salary slip -> AccessError expected
        with self.assertRaises(AccessError):
            salary_slip_algiers.with_user(self.user_director_oran).read(["name", "base_salary"])

    def test_04_paid_slip_verrouillage(self):
        """Test that a paid salary slip is read-only for everyone except Super Admin."""
        salary_slip = self.env["winners.salary"].with_user(self.user_super_admin).create({
            "teacher_id": self.teacher_algiers.id,
            "period_start": "2026-07-01",
            "period_end": "2026-07-31",
            "base_salary": 45000.0,
            "bonus": 1000.0,
            "bonus_justification": "Prime",
        })

        # Validate and Pay
        salary_slip.with_user(self.user_director_algiers).action_validate()
        salary_slip.with_user(self.user_director_algiers).action_pay()
        self.assertEqual(salary_slip.state, "paid")

        # Director tries to modify a paid slip -> UserError or AccessError expected
        with self.assertRaises(UserError):
            salary_slip.with_user(self.user_director_algiers).write({
                "base_salary": 55000.0,
            })

        # Super Admin is allowed to modify or reset it
        salary_slip.with_user(self.user_super_admin).action_reset_to_draft()
        self.assertEqual(salary_slip.state, "draft")
