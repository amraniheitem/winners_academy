# pyrefly: ignore [missing-import]
from odoo import api, models, tools


class IrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    @api.model
    @tools.ormcache('frozenset(self.env.user.groups_id.ids)', 'debug')
    def _visible_menu_ids(self, debug=False):
        """Override: non-admin Winners users only see the Winners Academy menu tree."""
        visible_ids = super()._visible_menu_ids(debug=debug)

        # Super Admin sees everything (Settings, Apps, Discuss, etc.)
        if self.env.user.has_group('winners_auth.winners_group_super_admin'):
            return visible_ids

        # For all other Winners roles, restrict to Winners Academy menu only
        root_menu = self.env.ref(
            'winners_branch.menu_winners_academy_root', raise_if_not_found=False
        )
        if not root_menu:
            return visible_ids

        # Walk each visible menu upward to check if it belongs to our root
        allowed = set()
        for menu in self.browse(visible_ids):
            current = menu
            while current:
                if current.id == root_menu.id:
                    # This menu is part of the Winners tree — keep it
                    allowed.add(menu.id)
                    break
                current = current.parent_id

        return allowed
