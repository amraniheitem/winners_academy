# pyrefly: ignore [missing-import]
from odoo.tests.common import TransactionCase
# pyrefly: ignore [missing-import]
from odoo.exceptions import AccessError, UserError
from odoo import fields
from datetime import date, timedelta


class TestAttendanceGeneration(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # ── 1. Créer une branche ──
        cls.branch = cls.env["winners.branch"].create({
            "name": "Branche Test Attendance",
            "is_active": True,
        })

        # ── 2. Créer une salle ──
        cls.room = cls.env["winners.room"].create({
            "name": "Salle Test 1",
            "branch_id": cls.branch.id,
            "capacity": 15,
        })

        # ── 3. Créer des enseignants ──
        cls.teacher = cls.env["winners.teacher"].create({
            "name": "Professeur Test",
            "specialty": "math",
            "branch_id": cls.branch.id,
        })

        # ── 4. Créer un groupe ──
        cls.group = cls.env["winners.group"].create({
            "name": "Math Test Group",
            "subject": "math",
            "level": "cem_4",
            "teacher_id": cls.teacher.id,
            "branch_id": cls.branch.id,
        })

        # ── 5. Créer des étudiants ──
        cls.student_1 = cls.env["winners.student"].create({
            "name": "Ben",
            "first_name": "Ali",
            "level": "cem_4",
            "sessions_remaining": 5,
            "status": "active",
            "branch_id": cls.branch.id,
        })
        cls.student_2 = cls.env["winners.student"].create({
            "name": "Bouzid",
            "first_name": "Fatima",
            "level": "cem_4",
            "sessions_remaining": 10,
            "status": "active",
            "branch_id": cls.branch.id,
        })
        cls.student_suspended = cls.env["winners.student"].create({
            "name": "Mourad",
            "first_name": "Ahmed",
            "level": "cem_4",
            "sessions_remaining": 5,
            "status": "suspended",
            "branch_id": cls.branch.id,
        })

        # Assigner les étudiants au groupe
        cls.group.write({
            "student_ids": [(6, 0, [cls.student_1.id, cls.student_2.id, cls.student_suspended.id])]
        })

        # ── 6. Créer un créneau récurrent (schedule) ──
        # Aujourd'hui en python :
        cls.today_date = date.today()
        # Jour de la semaine en anglais / odoo selection
        day_keys = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        cls.today_day_key = day_keys[cls.today_date.weekday()]

        cls.schedule = cls.env["winners.schedule"].create({
            "group_id": cls.group.id,
            "room_id": cls.room.id,
            "day_of_week": cls.today_day_key,
            "time_start": 14.0,  # 14h00
            "time_end": 15.5,    # 15h30
            "is_active": True,
        })

    def test_01_attendance_generation_and_duplicates(self):
        """Vérifie la génération automatique et l'absence de doublons."""
        SheetObj = self.env["winners.attendance.sheet"]

        # 1. Générer pour aujourd'hui
        sheets = SheetObj._generate_daily_sheets(target_date=self.today_date)
        self.assertTrue(sheets, "Une feuille de présence aurait dû être générée.")

        # Filtrer pour notre groupe de test
        sheet = sheets.filtered(lambda s: s.group_id.id == self.group.id)
        self.assertEqual(len(sheet), 1, "Il devrait y avoir exactement une feuille pour notre groupe de test.")
        self.assertEqual(sheet.group_id.id, self.group.id)
        self.assertEqual(sheet.time_start, 14.0)
        self.assertEqual(sheet.time_end, 15.5)
        self.assertEqual(sheet.state, "open")

        # Vérifier que seuls les étudiants non suspendus ont été ajoutés
        self.assertEqual(len(sheet.line_ids), 2, "La feuille devrait contenir 2 étudiants actifs.")
        student_ids = sheet.line_ids.mapped('student_id.id')
        self.assertIn(self.student_1.id, student_ids)
        self.assertIn(self.student_2.id, student_ids)
        self.assertNotIn(self.student_suspended.id, student_ids)

        # 2. Lancer à nouveau la génération pour le même jour (simuler relance cron)
        sheets_retry = SheetObj._generate_daily_sheets(target_date=self.today_date)
        self.assertFalse(sheets_retry, "Aucune feuille ne devrait être générée (anti-doublon).")

    def test_02_dynamic_student_addition(self):
        """Vérifie qu'un étudiant ajouté après la génération est rajouté aux feuilles ouvertes."""
        SheetObj = self.env["winners.attendance.sheet"]

        # Générer la feuille de présence
        sheets = SheetObj._generate_daily_sheets(target_date=self.today_date)
        sheet = sheets.filtered(lambda s: s.group_id.id == self.group.id)
        self.assertEqual(len(sheet.line_ids), 2)

        # Créer un nouvel étudiant
        new_student = self.env["winners.student"].create({
            "name": "Khelif",
            "first_name": "Salima",
            "level": "cem_4",
            "sessions_remaining": 8,
            "status": "active",
            "branch_id": self.branch.id,
        })

        # L'ajouter au groupe
        self.group.write({
            "student_ids": [(4, new_student.id)]
        })

        # Vérifier s'il a été ajouté automatiquement à la feuille du jour ouverte
        student_ids = sheet.line_ids.mapped('student_id.id')
        self.assertIn(new_student.id, student_ids, "Le nouvel étudiant aurait dû être ajouté dynamiquement.")
        self.assertEqual(len(sheet.line_ids), 3)

    def test_03_mark_present_and_session_deduction(self):
        """Vérifie le marquage de présence et la déduction automatique des séances."""
        SheetObj = self.env["winners.attendance.sheet"]

        # Générer la feuille de présence
        sheets = SheetObj._generate_daily_sheets(target_date=self.today_date)
        sheet = sheets.filtered(lambda s: s.group_id.id == self.group.id)

        line_1 = sheet.line_ids.filtered(lambda l: l.student_id.id == self.student_1.id)
        self.assertEqual(line_1.status, "absent")
        initial_sessions = self.student_1.sessions_remaining

        # Marquer comme présent
        line_1.mark_present(source='manual')
        self.assertEqual(line_1.status, "present")
        self.assertEqual(self.student_1.sessions_remaining, initial_sessions - 1, "Une séance aurait dû être déduite.")
        self.assertEqual(line_1.marked_by.id, self.env.uid)
        self.assertIsNotNone(line_1.marked_at)
        self.assertEqual(line_1.source, "manual")

        # Marquer comme absent (annulation de présence)
        line_1.mark_absent()
        self.assertEqual(line_1.status, "absent")
        self.assertEqual(self.student_1.sessions_remaining, initial_sessions, "La séance aurait dû être recréditée.")

    def test_04_sheet_readonly_on_closed(self):
        """Vérifie que la feuille clôturée est en lecture seule pour les non-admins."""
        SheetObj = self.env["winners.attendance.sheet"]

        # Générer la feuille
        sheets = SheetObj._generate_daily_sheets(target_date=self.today_date)
        sheet = sheets.filtered(lambda s: s.group_id.id == self.group.id)

        # Clôturer
        sheet.action_close()
        self.assertEqual(sheet.state, "closed")

        line = sheet.line_ids[0]

        # Simuler un enseignant ou autre rôle (non super admin) essayant d'éditer la ligne
        # On crée un utilisateur enseignant de test
        teacher_user = self.env["res.users"].create({
            "name": "Teacher User",
            "login": "teacher.attendance.test@winners.com",
            "winners_role": "teacher",
            "branch_id": self.branch.id,
        })

        # L'enseignant tente de changer le statut
        with self.assertRaises(UserError):
            line.with_user(teacher_user).write({
                "status": "present",
            })
