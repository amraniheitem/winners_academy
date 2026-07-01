# pyrefly: ignore [missing-import]
from odoo import api, fields, models
# pyrefly: ignore [missing-import]
from odoo.exceptions import UserError


class WinnersAttendance(models.Model):
    _name = "winners.attendance"
    _description = "Présence Winners"

    _sql_constraints = [
        (
            'unique_student_group_date',
            'UNIQUE(student_id, group_id, date)',
            'Cet étudiant a déjà une présence enregistrée pour ce groupe à cette date !',
        ),
    ]

    student_id = fields.Many2one(
        comodel_name="winners.student",
        string="Étudiant",
        required=True,
    )
    group_id = fields.Many2one(
        comodel_name="winners.group",
        string="Groupe",
        required=True,
    )
    date = fields.Date(
        string="Date",
        required=True,
        default=fields.Date.today,
    )
    status = fields.Selection(
        selection=[
            ("present", "Présent"),
            ("absent", "Absent"),
            ("late", "En retard"),
        ],
        string="Statut",
        default="present",
    )
    notes = fields.Text(
        string="Notes",
    )
    branch_id = fields.Many2one(
        comodel_name="winners.branch",
        string="Branche",
        related="group_id.branch_id",
        readonly=True,
        store=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if record.status == "present":
                record._deduct_session()
        return records

    def write(self, vals):
        old_statuses = {rec.id: rec.status for rec in self}
        result = super().write(vals)
        if 'status' in vals:
            for record in self:
                if vals['status'] == 'present' and old_statuses[record.id] != 'present':
                    record._deduct_session()
        return result

    def _deduct_session(self):
        """Décrémente les séances restantes et met à jour le statut de l'étudiant."""
        self.ensure_one()
        student = self.student_id
        if student.sessions_remaining <= 0:
            raise UserError(
                "L'étudiant %s n'a plus de séances restantes !" % student.name
            )
        student.sessions_remaining -= 1
        # Mise à jour du statut de l'étudiant
        if student.sessions_remaining > 2:
            student.status = "active"
        elif student.sessions_remaining >= 1:
            student.status = "alert"
        else:
            student.status = "expired"
