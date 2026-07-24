# -*- coding: utf-8 -*-
from datetime import date, timedelta
from odoo import _, api, models
from odoo.exceptions import UserError
from . import printer_service


class WinnersPaymentExt(models.Model):
    _inherit = 'winners.payment'

    def action_print_bon_paiement(self):
        """Imprime le bon de paiement sur l'imprimante thermique USB (Format 80mm)."""
        self.ensure_one()

        config = self.env['winners.printer.config'].search([('is_default', '=', True)], limit=1)
        if not config:
            config = self.env['winners.printer.config'].search([('active', '=', True)], limit=1)
        if not config:
            raise UserError(_("Aucune imprimante configurée. Veuillez configurer une imprimante dans le menu Imprimante."))

        try:
            v_id = int(config.vendor_id, 16)
            p_id = int(config.product_id, 16)
        except (ValueError, TypeError):
            raise UserError(_("Identifiants VendorID/ProductID invalides dans la configuration de l'imprimante."))

        # Libellé du mode de paiement
        payment_mode_label = 'Espèces'
        if self.payment_mode:
            selection = dict(self._fields['payment_mode'].selection)
            payment_mode_label = selection.get(self.payment_mode, self.payment_mode)

        # Nom et prénom de l'étudiant
        nom_etudiant = ''
        if self.student_id:
            nom_etudiant = f"{self.student_id.first_name or ''} {self.student_id.name or ''}".strip() or self.student_id.name or ''

        # Groupe, Matière et Niveau du groupe / étudiant
        groupe_name = self.group_id.name if self.group_id else ''
        matiere_name = ''
        niveau_name = ''

        if self.group_id:
            if getattr(self.group_id, 'subject', False):
                selection_sub = dict(self.group_id._fields['subject'].selection)
                matiere_name = selection_sub.get(self.group_id.subject, self.group_id.subject)
            if getattr(self.group_id, 'level', False):
                selection_lev = dict(self.group_id._fields['level'].selection)
                niveau_name = selection_lev.get(self.group_id.level, self.group_id.level)

        if not niveau_name and self.student_id and getattr(self.student_id, 'level', False):
            selection_lev = dict(self.student_id._fields['level'].selection)
            niveau_name = selection_lev.get(self.student_id.level, self.student_id.level)

        # Date de paiement et date du prochain versement (4 semaines / 28 jours après)
        payment_date = self.date or date.today()
        date_str = payment_date.strftime('%d/%m/%Y')
        next_date = payment_date + timedelta(days=28)
        next_date_str = next_date.strftime('%d/%m/%Y')

        # Séances restantes
        seances_restantes = getattr(self.student_id, 'sessions_remaining', 0)

        data = {
            'academy_name': config.academy_name or 'WINNERS ACADEMY',
            'branch_name': self.branch_id.name or config.branch_name or '',
            'nom_etudiant': nom_etudiant,
            'groupe': groupe_name,
            'matiere': matiere_name,
            'niveau': niveau_name,
            'montant': self.amount or 0.0,
            'mode_paiement': payment_mode_label,
            'seances_achetees': self.sessions_count or 0,
            'seances_restantes': seances_restantes,
            'date': date_str,
            'prochain_versement': next_date_str,
            'agent': self.env.user.name or '',
        }

        try:
            commands = printer_service.build_bon_paiement(data)
            printer_service.print_escpos(commands, vendor_id=v_id, product_id=p_id)
        except Exception as e:
            raise UserError(_("Erreur d'impression du bon de paiement : %s") % str(e))

        return True
