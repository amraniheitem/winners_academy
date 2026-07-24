# pyrefly: ignore [missing-import]
from odoo import _, api, fields, models
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
    group_id = fields.Many2one(
        comodel_name="winners.group",
        string="Groupe",
        required=True,
        domain="[('enrollment_ids.student_id', '=', student_id)]",
    )
    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.company.currency_id,
        required=True,
    )
    session_price = fields.Monetary(
        related="group_id.session_price",
        string="Prix de la séance (DA)",
        readonly=True,
        currency_field="currency_id",
    )
    date = fields.Date(
        string="Date de paiement",
        required=True,
        default=fields.Date.today,
    )
    amount = fields.Float(
        string="Montant",
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
        string="Statut",
        default="draft",
    )

    @api.onchange('amount', 'group_id')
    def _onchange_amount_group(self):
        if self.session_price and self.session_price > 0:
            self.sessions_count = int(self.amount / self.session_price)

    def action_confirm(self):
        for record in self:
            if record.state == "confirmed":
                continue
            if record.sessions_count <= 0:
                raise UserError(
                    _("Le nombre de séances achetées doit être supérieur à zéro.")
                )
            
            # Rechercher l'inscription correspondante
            enrollment = self.env['winners.student.enrollment'].search([
                ('student_id', '=', record.student_id.id),
                ('group_id', '=', record.group_id.id),
            ], limit=1)
            
            if not enrollment:
                raise UserError(
                    _("L'étudiant n'a pas d'inscription active ou suspendue dans le groupe %s.") % record.group_id.name
                )
                
            record.state = "confirmed"
            # Ajouter les séances au solde de l'inscription correspondante
            enrollment.sessions_remaining += record.sessions_count
