# -*- coding: utf-8 -*-
from datetime import date
from odoo import models, api
from odoo.exceptions import UserError
from . import printer_service


class WinnersSalaryExt(models.Model):
    _inherit = 'winners.salary'

    def action_print_bordereau(self):
        """Imprime le bulletin de salaire sur l'imprimante thermique USB (Format 80mm)."""
        self.ensure_one()

        config = self.env['winners.printer.config'].search([('is_default', '=', True)], limit=1)
        if not config:
            config = self.env['winners.printer.config'].search([('active', '=', True)], limit=1)
        if not config:
            raise UserError("Aucune imprimante configurée. Veuillez configurer une imprimante dans le menu Imprimante.")

        try:
            v_id = int(config.vendor_id, 16)
            p_id = int(config.product_id, 16)
        except (ValueError, TypeError):
            raise UserError("Identifiants VendorID/ProductID invalides dans la configuration de l'imprimante.")

        # Période sous forme MM/YYYY
        periode_str = ''
        if self.period_start:
            periode_str = self.period_start.strftime('%m/%Y')

        # Statut lisible
        state_label = ''
        if self.state:
            selection = dict(self._fields['state'].selection)
            state_label = selection.get(self.state, self.state)

        date_str = date.today().strftime('%d/%m/%Y')

        data = {
            'academy_name': config.academy_name or 'WINNERS ACADEMY',
            'branch_name': self.branch_id.name or config.branch_name or '',
            'nom_employe': self.teacher_id.name if self.teacher_id else '',
            'poste': 'Enseignant',
            'periode': periode_str,
            'salaire_net': self.net_salary or 0.0,
            'state_label': state_label.upper() if state_label else '',
            'date': date_str,
        }

        try:
            commands = printer_service.build_bordereau_salaire(data)
            printer_service.print_escpos(commands, vendor_id=v_id, product_id=p_id)
        except Exception as e:
            raise UserError(f"Erreur d'impression du bulletin de salaire : {str(e)}")

        return True
