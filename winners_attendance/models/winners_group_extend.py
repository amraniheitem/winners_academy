# pyrefly: ignore [missing-import]
from odoo import api, models, fields
import logging

_logger = logging.getLogger(__name__)


class WinnersGroup(models.Model):
    _inherit = "winners.group"

    def write(self, vals):
        """
        Surcharge de la méthode write pour détecter si un étudiant est ajouté
        au groupe et, le cas échéant, l'ajouter automatiquement aux feuilles
        de présence de ce groupe créées pour aujourd'hui et non encore clôturées.
        """
        # Sauvegarder les étudiants avant écriture
        old_students_map = {g.id: set(g.student_ids.ids) for g in self}
        
        res = super(WinnersGroup, self).write(vals)

        # Si student_ids est mis à jour, vérifier les nouveaux étudiants
        if 'student_ids' in vals:
            today = fields.Date.today()
            AttendanceSheet = self.env['winners.attendance.sheet']
            AttendanceLine = self.env['winners.attendance.line']

            for group in self:
                old_ids = old_students_map.get(group.id, set())
                current_ids = set(group.student_ids.ids)
                new_ids = current_ids - old_ids

                if not new_ids:
                    continue

                # Récupérer les feuilles du jour non clôturées pour ce groupe
                sheets = AttendanceSheet.search([
                    ('group_id', '=', group.id),
                    ('date', '=', today),
                    ('state', 'in', ['open', 'in_progress']),
                ])

                if not sheets:
                    continue

                # Pour chaque feuille ouverte, créer une ligne de présence pour les nouveaux étudiants
                for sheet in sheets:
                    existing_student_ids = set(sheet.line_ids.mapped('student_id.id'))
                    lines_to_create = []
                    for s_id in new_ids:
                        student = self.env['winners.student'].browse(s_id)
                        if student.status == 'suspended':
                            continue
                        if s_id not in existing_student_ids:
                            lines_to_create.append({
                                'sheet_id': sheet.id,
                                'student_id': s_id,
                                'status': 'absent',
                            })

                    if lines_to_create:
                        AttendanceLine.create(lines_to_create)
                        _logger.info(
                            "Dynamically added %d new student(s) to attendance sheet %s of group %s",
                            len(lines_to_create), sheet.display_name, group.name
                        )
        return res
