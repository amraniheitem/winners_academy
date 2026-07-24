# pyrefly: ignore [missing-import]
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError
from datetime import date


class TestWinnersEnrollment(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create branch
        cls.branch = cls.env["winners.branch"].create({
            "name": "Branche Test Enrollment",
            "is_active": True,
        })

        # Create room
        cls.room = cls.env["winners.room"].create({
            "name": "Salle Test E1",
            "branch_id": cls.branch.id,
            "capacity": 20,
        })

        # Create teacher
        cls.teacher = cls.env["winners.teacher"].create({
            "name": "Professeur Enrollment Test",
            "specialty": "math",
            "branch_id": cls.branch.id,
        })

        # Create groups for math, arabic, english
        cls.group_math = cls.env["winners.group"].create({
            "name": "Math Group",
            "subject": "math",
            "level": "cem_4",
            "teacher_id": cls.teacher.id,
            "branch_id": cls.branch.id,
            "session_price": 500.0,
        })
        cls.group_arabic = cls.env["winners.group"].create({
            "name": "Arabic Group",
            "subject": "arabic",
            "level": "cem_4",
            "teacher_id": cls.teacher.id,
            "branch_id": cls.branch.id,
            "session_price": 400.0,
        })
        cls.group_english = cls.env["winners.group"].create({
            "name": "English Group",
            "subject": "english",
            "level": "cem_4",
            "teacher_id": cls.teacher.id,
            "branch_id": cls.branch.id,
            "session_price": 600.0,
        })

        # Create student
        cls.student = cls.env["winners.student"].create({
            "name": "Amrani",
            "first_name": "Haitem",
            "level": "cem_4",
            "branch_id": cls.branch.id,
        })

    def test_01_multi_enrollment_independent_counters(self):
        """Student enrolled in 3 groups -> 3 distinct enrollments, independent counters."""
        EnrollmentObj = self.env["winners.student.enrollment"]

        # Create enrollments
        enroll_math = EnrollmentObj.create({
            "student_id": self.student.id,
            "group_id": self.group_math.id,
            "sessions_remaining": 5,
        })
        enroll_arabic = EnrollmentObj.create({
            "student_id": self.student.id,
            "group_id": self.group_arabic.id,
            "sessions_remaining": 3,
        })
        enroll_english = EnrollmentObj.create({
            "student_id": self.student.id,
            "group_id": self.group_english.id,
            "sessions_remaining": 10,
        })

        # Verify they are separate and have correct status
        self.assertEqual(enroll_math.status, "active")
        self.assertEqual(enroll_arabic.status, "active")
        self.assertEqual(enroll_english.status, "active")

        # Verify student computed totals
        self.student.flush_record_values()
        self.assertEqual(self.student.sessions_remaining, 18)
        self.assertEqual(self.student.status, "active")

        # Verify unique constraint (cannot enroll again in math)
        with self.assertRaises(Exception):
            with self.cr.savepoint():
                EnrollmentObj.create({
                    "student_id": self.student.id,
                    "group_id": self.group_math.id,
                    "sessions_remaining": 2,
                })

    def test_02_payment_specific_group(self):
        """Payment on specific group only increments that group's counter."""
        EnrollmentObj = self.env["winners.student.enrollment"]
        PaymentObj = self.env["winners.payment"]

        # Create enrollments
        enroll_math = EnrollmentObj.create({
            "student_id": self.student.id,
            "group_id": self.group_math.id,
            "sessions_remaining": 2,
        })
        enroll_arabic = EnrollmentObj.create({
            "student_id": self.student.id,
            "group_id": self.group_arabic.id,
            "sessions_remaining": 1,
        })

        # math price is 500 DA. We pay 1500 DA, expecting 3 sessions.
        payment = PaymentObj.create({
            "student_id": self.student.id,
            "group_id": self.group_math.id,
            "amount": 1500.0,
            "payment_mode": "cash",
            "branch_id": self.branch.id,
        })
        # Trigger onchange manually to verify count suggestion
        payment._onchange_amount_group()
        self.assertEqual(payment.sessions_count, 3)

        # Confirm payment
        payment.action_confirm()
        self.assertEqual(payment.state, "confirmed")

        # Verify math sessions increased by 3 (from 2 to 5), arabic unchanged (still 1)
        self.assertEqual(enroll_math.sessions_remaining, 5)
        self.assertEqual(enroll_arabic.sessions_remaining, 1)

        # Verify student computed totals
        self.student.flush_record_values()
        self.assertEqual(self.student.sessions_remaining, 6)

    def test_03_attendance_deduction_specific_group(self):
        """Attendance sheet check-in decrements correct enrollment counter."""
        EnrollmentObj = self.env["winners.student.enrollment"]
        SheetObj = self.env["winners.attendance.sheet"]

        # Create enrollments
        enroll_math = EnrollmentObj.create({
            "student_id": self.student.id,
            "group_id": self.group_math.id,
            "sessions_remaining": 4,
        })
        enroll_arabic = EnrollmentObj.create({
            "student_id": self.student.id,
            "group_id": self.group_arabic.id,
            "sessions_remaining": 6,
        })

        # Create manual attendance sheet for math
        sheet_math = SheetObj.create({
            "date": date.today(),
            "group_id": self.group_math.id,
            "time_start": 9.0,
            "time_end": 10.5,
            "state": "open",
        })
        sheet_math._populate_lines()

        # Find line
        line = sheet_math.line_ids.filtered(lambda l: l.student_id == self.student)
        self.assertTrue(line, "Student should have a line in the sheet.")

        # Mark present
        line.mark_present(source='manual')
        self.assertEqual(line.status, "present")

        # Math count should be 3, Arabic should be 6 (unchanged)
        self.assertEqual(enroll_math.sessions_remaining, 3)
        self.assertEqual(enroll_arabic.sessions_remaining, 6)
