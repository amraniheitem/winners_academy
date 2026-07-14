# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class WinnersAttendanceAddStudentWizard(models.TransientModel):
    _name = "winners.attendance.add.student.wizard"
    _description = "Wizard pour ajouter un étudiant manuellement"

    sheet_id = fields.Many2one(
        comodel_name="winners.attendance.sheet",
        string="Feuille de présence",
        required=True,
        readonly=True,
    )
    student_id = fields.Many2one(
        comodel_name="winners.student",
        string="Étudiant",
        required=True,
    )
    status = fields.Selection(
        selection=[
            ("present", "Présent"),
            ("late", "En retard"),
            ("absent", "Absent"),
        ],
        string="Statut",
        default="present",
        required=True,
    )

    def action_confirm(self):
        self.ensure_one()
        
        # Vérifier si l'étudiant a déjà une ligne
        Line = self.env['winners.attendance.line']
        existing = Line.search([
            ('sheet_id', '=', self.sheet_id.id),
            ('student_id', '=', self.student_id.id),
        ], limit=1)

        if existing:
            raise UserError(
                f"L'étudiant {self.student_id.name} a déjà une ligne "
                "sur cette feuille de présence !"
            )

        # Créer la ligne de présence (initialisée à absent)
        new_line = Line.create({
            'sheet_id': self.sheet_id.id,
            'student_id': self.student_id.id,
            'status': 'absent',
        })

        # Mettre à jour le statut via les méthodes de validation centralisées
        # pour gérer correctement les séances d'abonnement restantes
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
                'title': 'Étudiant ajouté',
                'message': f"{self.student_id.name} a été ajouté avec succès.",
                'type': 'success',
                'sticky': False,
            }
        }
