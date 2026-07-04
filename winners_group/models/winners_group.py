# pyrefly: ignore [missing-import]
from odoo import api, fields, models


class WinnersGroup(models.Model):
    _name = "winners.group"
    _description = "Groupe Winners"
    _rec_name = "name"

    name = fields.Char(
        string="Nom du groupe",
        required=True,
    )
    teacher_id = fields.Many2one(
        comodel_name="winners.teacher",
        string="Enseignant",
    )
    subject = fields.Selection(
        selection=[
            ("arabic", "Arabe"),
            ("french", "Français"),
            ("math", "Mathématiques"),
            ("science", "Sciences"),
            ("english", "Anglais"),
        ],
        string="Matière",
    )
    level = fields.Selection(
        selection=[
            ("primaire_1", "Primaire 1"),
            ("primaire_2", "Primaire 2"),
            ("primaire_3", "Primaire 3"),
            ("primaire_4", "Primaire 4"),
            ("primaire_5", "Primaire 5"),
            ("cem_1", "CEM 1"),
            ("cem_2", "CEM 2"),
            ("cem_3", "CEM 3"),
            ("cem_4", "CEM 4"),
            ("lycee_1", "Lycée 1"),
            ("lycee_2", "Lycée 2"),
            ("lycee_3", "Lycée 3"),
        ],
        string="Niveau scolaire",
    )
    branch_id = fields.Many2one(
        comodel_name="winners.branch",
        string="Branche",
        default=lambda self: self.env.user.branch_id,
    )
    student_ids = fields.Many2many(
        comodel_name="winners.student",
        string="Élèves",
    )
    max_students = fields.Integer(
        string="Nombre max d'élèves",
        default=15,
    )
    nb_students = fields.Integer(
        string="Nombre d'élèves",
        compute="_compute_nb_students",
        store=True,
    )
    is_active = fields.Boolean(
        string="Actif",
        default=True,
    )

    @api.depends("student_ids")
    def _compute_nb_students(self):
        for record in self:
            record.nb_students = len(record.student_ids)
