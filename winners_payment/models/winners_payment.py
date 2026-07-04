# pyrefly: ignore [missing-import]
from odoo import fields, models
# pyrefly: ignore [missing-import]
from odoo.exceptions import UserError


class WinnersPayment(models.Model):
    _name = "winners.payment"
    _description = "Paiement Winners"

    student_id = fields.Many2one(
        comodel_name="winners.student",
        string="Étudiant",
        required=True,
    )
    date = fields.Date(
        string="Date de paiement",
        required=True,
        default=fields.Date.today,
    )
    amount = fields.Float(
        string="Montant (DA)",
        required=True,
    )
    sessions_count = fields.Integer(
        string="Séances achetées",
        required=True,
    )
    payment_mode = fields.Selection(
        selection=[
            ("cash", "Espèces"),
            ("transfer", "Virement"),
        ],
        string="Mode de paiement",
        default="cash",
    )
    branch_id = fields.Many2one(
        comodel_name="winners.branch",
        string="Branche",
        default=lambda self: self.env.user.branch_id,
    )
    notes = fields.Text(
        string="Notes",
    )
    state = fields.Selection(
        selection=[
            ("draft", "Brouillon"),
            ("confirmed", "Confirmé"),
        ],
        string="État",
        default="draft",
    )

    def action_confirm(self):
        for record in self:
            if record.sessions_count <= 0:
                raise UserError(
                    "Le nombre de séances achetées doit être supérieur à zéro."
                )
            record.state = "confirmed"
            # Ajouter les séances au solde de l'étudiant
            student = record.student_id
            student.sessions_remaining += record.sessions_count
            # Mettre à jour le statut de l'étudiant
            if student.sessions_remaining > 2:
                student.status = "active"
            elif student.sessions_remaining >= 1:
                student.status = "alert"
            else:
                student.status = "expired"

