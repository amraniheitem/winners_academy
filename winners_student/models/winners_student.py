from odoo import fields, models


class WinnersStudent(models.Model):
    _name = "winners.student"
    _description = "Élève Winners"
    _rec_name = "name"

    name = fields.Char(
        string="Nom de famille",
        required=True,
    )
    first_name = fields.Char(
        string="Prénom",
    )
    birth_date = fields.Date(
        string="Date de naissance",
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
    photo = fields.Image(
        string="Photo",
    )
    parent_name = fields.Char(
        string="Nom du parent",
    )
    parent_phone = fields.Char(
        string="Téléphone parent",
    )
    parent_address = fields.Text(
        string="Adresse parent",
    )
    status = fields.Selection(
        selection=[
            ("active", "Actif"),
            ("alert", "Alerte"),
            ("expired", "Expiré"),
            ("suspended", "Suspendu"),
        ],
        default="active",
    )
    sessions_remaining = fields.Integer(
        string="Séances restantes",
        default=0,
    )
    enrollment_date = fields.Date(
        string="Date d'inscription",
        default=fields.Date.today,
    )
    branch_id = fields.Many2one(
        comodel_name="winners.branch",
        string="Branche",
        default=lambda self: self.env.user.branch_id,
    )
