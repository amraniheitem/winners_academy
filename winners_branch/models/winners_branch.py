# pyrefly: ignore [missing-import]
from odoo import fields, models


class WinnersBranch(models.Model):
    _name = "winners.branch"
    _description = "Branche Winners"
    _rec_name = "name"

    name = fields.Char(
        string="Nom de la branche",
        required=True,
    )
    address = fields.Text(
        string="Adresse",
    )
    phone = fields.Char(
        string="Téléphone",
    )
    is_active = fields.Boolean(
        string="Actif",
        default=True,
    )
