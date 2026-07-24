# pyrefly: ignore [missing-import]
from odoo import fields, models, api


class ResUsers(models.Model):
    _inherit = "res.users"

    winners_role = fields.Selection(
        selection=[
            ("super_admin", "Super administrateur"),
            ("director", "Directeur"),
            ("secretary", "Secrétaire"),
            ("teacher", "Enseignant"),
            ("cashier", "Caissier"),
        ],
        string="Rôle Winners",
        default="secretary",
    )
    branch_id = fields.Many2one(
        comodel_name="winners.branch",
        string="Branche",
    )
    is_active_winners = fields.Boolean(
        string="Actif Winners",
        default=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        for user in users:
            if user.winners_role:
                user._sync_winners_groups()
        return users

    def write(self, vals):
        res = super().write(vals)
        if 'winners_role' in vals:
            for user in self:
                user._sync_winners_groups()
        return res

    def _sync_winners_groups(self):
        self.ensure_one()
        role_group_map = {
            'super_admin': 'winners_auth.winners_group_super_admin',
            'director': 'winners_auth.winners_group_director',
            'secretary': 'winners_auth.winners_group_secretary',
            'teacher': 'winners_auth.winners_group_teacher',
            'cashier': 'winners_auth.winners_group_cashier',
        }
        
        groups_to_remove = self.env['res.groups']
        group_to_add = self.env['res.groups']
        
        for role, xml_id in role_group_map.items():
            group = self.env.ref(xml_id, raise_if_not_found=False)
            if not group:
                continue
            if role == self.winners_role:
                group_to_add = group
            else:
                groups_to_remove |= group
                
        current_groups = self.groups_id
        to_remove = groups_to_remove & current_groups
        to_add = group_to_add - current_groups if group_to_add else self.env['res.groups']
        
        group_commands = []
        if to_remove:
            for g in to_remove:
                group_commands.append((3, g.id))
        if to_add:
            for g in to_add:
                group_commands.append((4, g.id))
                
        if group_commands:
            # Bypass self.write recursive loop
            super(ResUsers, self).write({'groups_id': group_commands})

        # Set home action to Winners Dashboard so user lands there after login
        dashboard_action = self.env.ref(
            'winners_dashboard.action_winners_dashboard',
            raise_if_not_found=False,
        )
        if dashboard_action and self.action_id != dashboard_action:
            super(ResUsers, self).write({
                'action_id': dashboard_action.id,
            })

    @api.model
    def set_user_language(self, lang_code):
        """
        Définit la langue de l'utilisateur connecté ('fr_FR', 'ar_001', 'ar_SA', etc.).
        Active automatiquement la langue dans la base Odoo si nécessaire.
        """
        user = self.env.user
        ResLang = self.env['res.lang'].sudo()

        # Si le code demandé est un code arabe générique ou spécifique
        target_code = lang_code
        lang = ResLang.search([('code', '=', target_code)], limit=1)

        if not lang and target_code.startswith('ar'):
            # Chercher n'importe quelle variante arabe disponible
            lang = ResLang.search([('code', '=like', 'ar%')], limit=1)
            if lang:
                target_code = lang.code

        if not lang:
            try:
                ResLang._activate_lang(target_code)
                lang = ResLang.search([('code', '=', target_code)], limit=1)
            except Exception:
                pass

        if lang and not lang.active:
            lang.write({'active': True})

        if user.lang != target_code:
            user.sudo().write({'lang': target_code})
        return {
            'success': True,
            'lang': target_code,
        }

