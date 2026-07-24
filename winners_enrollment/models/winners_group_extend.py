# pyrefly: ignore [missing-import]
from odoo import api, fields, models


class WinnersGroup(models.Model):
    _inherit = "winners.group"

    enrollment_ids = fields.One2many(
        comodel_name="winners.student.enrollment",
        inverse_name="group_id",
        string="Inscriptions",
    )

    student_ids = fields.Many2many(
        comodel_name="winners.student",
        string="Élèves",
        compute="_compute_student_ids",
        inverse="_inverse_student_ids",
        store=True,
    )

    @api.depends('enrollment_ids.student_id', 'enrollment_ids.status')
    def _compute_student_ids(self):
        for group in self:
            active_enrollments = group.enrollment_ids.filtered(lambda e: e.status != 'suspended')
            group.student_ids = [(6, 0, active_enrollments.mapped('student_id').ids)]

    def _inverse_student_ids(self):
        Enrollment = self.env['winners.student.enrollment']
        for group in self:
            current_students = group.enrollment_ids.filtered(lambda e: e.status != 'suspended').mapped('student_id')
            new_students = group.student_ids
            
            # Students to add
            for student in (new_students - current_students):
                suspended = group.enrollment_ids.filtered(
                    lambda e: e.student_id == student and e.status == 'suspended'
                )
                if suspended:
                    suspended.action_reactivate()
                else:
                    Enrollment.create({
                        'student_id': student.id,
                        'group_id': group.id,
                        'sessions_remaining': 0,
                    })
            
            # Students to remove
            for student in (current_students - new_students):
                to_remove = group.enrollment_ids.filtered(
                    lambda e: e.student_id == student
                )
                to_remove.unlink()
