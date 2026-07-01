# pyrefly: ignore [missing-import]
from odoo import api, fields, models
# pyrefly: ignore [missing-import]
from odoo.exceptions import ValidationError


class WinnersSchedule(models.Model):
    _name = "winners.schedule"
    _description = "Emploi du temps Winners"

    _sql_constraints = [
        (
            'unique_room_day_time',
            'UNIQUE(room_id, day_of_week, time_start)',
            'Cette salle est déjà occupée à ce créneau horaire !',
        ),
    ]

    group_id = fields.Many2one(
        comodel_name="winners.group",
        string="Groupe",
        required=True,
    )
    teacher_id = fields.Many2one(
        comodel_name="winners.teacher",
        string="Enseignant",
        related="group_id.teacher_id",
        readonly=True,
        store=True,
    )
    room_id = fields.Many2one(
        comodel_name="winners.room",
        string="Salle",
        required=True,
    )
    day_of_week = fields.Selection(
        selection=[
            ("monday", "Lundi"),
            ("tuesday", "Mardi"),
            ("wednesday", "Mercredi"),
            ("thursday", "Jeudi"),
            ("friday", "Vendredi"),
            ("saturday", "Samedi"),
            ("sunday", "Dimanche"),
        ],
        string="Jour",
        required=True,
    )
    time_start = fields.Float(
        string="Heure début",
        required=True,
    )
    time_end = fields.Float(
        string="Heure fin",
        required=True,
    )
    branch_id = fields.Many2one(
        comodel_name="winners.branch",
        string="Branche",
        related="room_id.branch_id",
        readonly=True,
        store=True,
    )
    is_active = fields.Boolean(
        string="Actif",
        default=True,
    )

    @api.constrains('time_start', 'time_end')
    def _check_time(self):
        for record in self:
            if record.time_end <= record.time_start:
                raise ValidationError(
                    "L'heure de fin doit être supérieure à l'heure de début."
                )
