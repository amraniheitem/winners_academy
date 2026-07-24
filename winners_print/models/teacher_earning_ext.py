# -*- coding: utf-8 -*-
from datetime import date
from odoo import models, api
from odoo.exceptions import UserError
from . import printer_service


class WinnersTeacherEarningSheetExt(models.Model):
    _inherit = 'winners.teacher.earning.sheet'

    def action_print_bordereau(self):
        """Imprime le bordereau de gains enseignant sur l'imprimante thermique USB (Format 80mm)."""
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

        periode_str = ''
        if self.period_start and self.period_end:
            periode_str = f"{self.period_start.strftime('%d/%m/%Y')} - {self.period_end.strftime('%d/%m/%Y')}"

        state_label = 'Traite' if self.state == 'treated' else 'Non traite'
        date_str = date.today().strftime('%d/%m/%Y')

        # Nombre total d'étudiants (présences comptabilisées)
        total_students = self.total_present_count or 0

        data = {
            'academy_name': config.academy_name or 'WINNERS ACADEMY',
            'branch_name': self.branch_id.name or config.branch_name or '',
            'ref': self.name or f"GAIN-{self.id:05d}",
            'nom_enseignant': self.teacher_id.name if self.teacher_id else '',
            'groupe': self.group_id.name if self.group_id else '',
            'periode': periode_str,
            'seances_faites': len(self.line_ids) if self.line_ids else 0,
            'nb_etudiants': total_students,
            'prix_seance': self.session_price or 0.0,
            'pourcentage': self.commission_percentage or 0.0,
            'montant_total': self.total_amount or 0.0,
            'montant_enseignant': self.teacher_amount or 0.0,
            'state_label': state_label.upper(),
            'date': date_str,
        }

        try:
            commands = printer_service.build_bordereau_enseignant(data)
            printer_service.print_escpos(commands, vendor_id=v_id, product_id=p_id)
        except Exception as e:
            raise UserError(f"Erreur d'impression du bordereau d'enseignant : {str(e)}")

        return True
