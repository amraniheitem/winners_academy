# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class WinnersAttendanceAddStudentWizard(models.TransientModel):
    _name = "winners.attendance.add.student.wizard"
    _description = "Wizard pour ajouter un etudiant manuellement"

    sheet_id = fields.Many2one(
        comodel_name="winners.attendance.sheet",
        string="Feuille de presence",
        required=True,
        readonly=True,
    )
    student_id = fields.Many2one(
        comodel_name="winners.student",
        string="Etudiant",
        required=True,
    )
    available_student_ids = fields.Many2many(
        comodel_name="winners.student",
        compute="_compute_available_student_ids",
    )
    status = fields.Selection(
        selection=[
            ("present", "Present"),
            ("late", "En retard"),
            ("absent", "Absent"),
        ],
        string="Statut",
        default="present",
        required=True,
    )

    @api.depends(
        "sheet_id",
        "sheet_id.group_id",
        "sheet_id.group_id.student_ids",
        "sheet_id.group_id.enrollment_ids",
        "sheet_id.group_id.enrollment_ids.status",
        "sheet_id.group_id.enrollment_ids.student_id",
    )
    def _compute_available_student_ids(self):
        for wizard in self:
            active_enrollments = wizard.sheet_id.group_id.enrollment_ids.filtered(
                lambda enrollment: enrollment.status == "active"
            )
            wizard.available_student_ids = (
                active_enrollments.mapped("student_id")
                or wizard.sheet_id.group_id.student_ids
            )

    def action_confirm(self):
        self.ensure_one()

        if self.student_id not in self.available_student_ids:
            raise UserError(
                "Cet etudiant n'appartient pas au groupe de cette feuille de presence."
            )

        Line = self.env['winners.attendance.line']
        existing = Line.search([
            ('sheet_id', '=', self.sheet_id.id),
            ('student_id', '=', self.student_id.id),
        ], limit=1)

        if existing:
            raise UserError(
                f"L'etudiant {self.student_id.name} a deja une ligne "
                "sur cette feuille de presence !"
            )

        new_line = Line.create({
            'sheet_id': self.sheet_id.id,
            'student_id': self.student_id.id,
            'status': 'absent',
        })

        if self.status == 'present':
            new_line.mark_present(source='manual')
        elif self.status == 'late':
            new_line.mark_late(source='manual')
        else:
            new_line.mark_absent()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Etudiant ajoute',
                'message': f"{self.student_id.name} a ete ajoute avec succes.",
                'type': 'success',
                'sticky': False,
            }
        }
