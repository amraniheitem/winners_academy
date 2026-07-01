# pyrefly: ignore [missing-import]
from odoo import fields, models


class WinnersRoom(models.Model):
    _name = "winners.room"
    _description = "Salle Winners"

    name = fields.Char(
        string="Nom de la salle",
        required=True,
    )
    capacity = fields.Integer(
        string="Capacité (places)",
        default=20,
    )
    branch_id = fields.Many2one(
        comodel_name="winners.branch",
        string="Branche",
        required=True,
    )
    floor = fields.Char(
        string="Étage",
    )
    equipment = fields.Text(
        string="Équipements",
    )
    is_active = fields.Boolean(
        string="Disponible",
        default=True,
    )
