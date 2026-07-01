from odoo import fields, models


class WinnersSession(models.Model):
    _name = "winners.session"
    _description = "Séance Winners"

    group_id = fields.Many2one(
        comodel_name="winners.group",
        string="Groupe",
        required=True,
    )
    date = fields.Datetime(
        string="Date et heure",
        required=True,
    )
    duration_hours = fields.Float(
        string="Durée (heures)",
        default=1.5,
    )
    status = fields.Selection(
        selection=[
            ("planned", "Planifiée"),
            ("done", "Terminée"),
            ("cancelled", "Annulée"),
        ],
        string="Statut",
        default="planned",
    )
    notes = fields.Text(
        string="Notes",
    )
