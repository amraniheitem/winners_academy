from odoo import fields, models


class WinnersTeacher(models.Model):
    _name = "winners.teacher"
    _description = "Enseignant Winners"
    _rec_name = "name"

    name = fields.Char(
        string="Nom complet",
        required=True,
    )
    phone = fields.Char(
        string="Téléphone",
    )
    specialty = fields.Selection(
        selection=[
            ("arabic", "Arabe"),
            ("french", "Français"),
            ("math", "Mathématiques"),
            ("science", "Sciences"),
            ("english", "Anglais"),
        ],
        string="Matière",
    )
    hire_date = fields.Date(
        string="Date d'embauche",
    )
    branch_id = fields.Many2one(
        comodel_name="winners.branch",
        string="Branche",
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Compte utilisateur",
    )
    is_active = fields.Boolean(
        string="Actif",
        default=True,
    )

    def action_create_user(self):
        for teacher in self:
            if teacher.user_id:
                continue
            
            email = getattr(teacher, 'email', False)
            if not email:
                clean_name = "".join(c for c in (teacher.name or "") if c.isalnum() or c in ['.', '_', '-']).lower()
                clean_name = clean_name.replace(" ", "")
                phone_part = teacher.phone or str(teacher.id)
                email = f"{clean_name}.{phone_part}@winners.com"
                
            user_vals = {
                'name': teacher.name,
                'login': email,
                'email': email,
                'winners_role': 'teacher',
                'branch_id': teacher.branch_id.id if teacher.branch_id else False,
            }
            user = self.env['res.users'].create(user_vals)
            teacher.user_id = user.id

