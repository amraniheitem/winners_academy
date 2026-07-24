# pyrefly: ignore [missing-import]
from odoo import api, fields, models


class WinnersStudent(models.Model):
    _inherit = "winners.student"

    enrollment_ids = fields.One2many(
        comodel_name="winners.student.enrollment",
        inverse_name="student_id",
        string="Inscriptions par groupe",
    )

    # Override sessions_remaining to be computed and stored
    sessions_remaining = fields.Integer(
        string="Séances restantes",
        compute="_compute_sessions_remaining",
        store=True,
        readonly=True,
    )

    # Override status to be computed and stored
    status = fields.Selection(
        selection=[
            ("active", "Actif"),
            ("alert", "Alerte"),
            ("expired", "Expiré"),
            ("suspended", "Suspendu"),
        ],
        string="Statut",
        compute="_compute_status_from_enrollments",
        store=True,
        readonly=True,
    )

    @api.depends('enrollment_ids.sessions_remaining')
    def _compute_sessions_remaining(self):
        for student in self:
            student.sessions_remaining = sum(
                student.enrollment_ids.mapped('sessions_remaining')
            )

    @api.depends('enrollment_ids.status')
    def _compute_status_from_enrollments(self):
        for student in self:
            statuses = student.enrollment_ids.mapped('status')
            if not statuses:
                student.status = 'expired'
            elif all(s == 'suspended' for s in statuses):
                student.status = 'suspended'
            else:
                active_statuses = [s for s in statuses if s != 'suspended']
                if not active_statuses:
                    student.status = 'suspended'
                elif 'expired' in active_statuses:
                    student.status = 'expired'
                elif 'alert' in active_statuses:
                    student.status = 'alert'
                else:
                    student.status = 'active'
    schedule_ids = fields.Many2many(
        comodel_name="winners.schedule",
        string="Créneaux horaires",
        compute="_compute_schedule_ids",
    )

    @api.depends('enrollment_ids.group_id', 'enrollment_ids.status')
    def _compute_schedule_ids(self):
        Schedule = self.env['winners.schedule']
        for student in self:
            active_groups = student.enrollment_ids.filtered(lambda e: e.status != 'suspended').mapped('group_id')
            if active_groups:
                student.schedule_ids = Schedule.search([
                    ('group_id', 'in', active_groups.ids),
                    ('is_active', '=', True),
                ])
            else:
                student.schedule_ids = False

    def action_print_schedule(self):
        self.ensure_one()
        return self.env.ref('winners_print.action_report_student_schedule').report_action(self)

    def get_sorted_schedules(self):
        self.ensure_one()
        days_order = {
            "monday": 1,
            "tuesday": 2,
            "wednesday": 3,
            "thursday": 4,
            "friday": 5,
            "saturday": 6,
            "sunday": 7,
        }
        return sorted(self.schedule_ids, key=lambda s: (days_order.get(s.day_of_week, 8), s.time_start))
