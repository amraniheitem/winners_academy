# -*- coding: utf-8 -*-
# pyrefly: ignore [missing-import]
from odoo import api, fields, models
import pytz
from datetime import datetime

class WinnersScheduleExtend(models.Model):
    _inherit = "winners.schedule"

    def action_open_attendance_sheet(self):
        """
        Recherche ou crée la feuille de présence d'aujourd'hui
        pour ce créneau et l'ouvre dans Odoo.
        """
        self.ensure_one()
        today = fields.Date.today()
        Sheet = self.env['winners.attendance.sheet']
        
        # Rechercher une feuille existante pour ce créneau et aujourd'hui
        sheet = Sheet.search([
            ('schedule_id', '=', self.id),
            ('date', '=', today),
        ], limit=1)

        if not sheet:
            # Créer la feuille à la demande
            sheet = Sheet.create({
                'date': today,
                'schedule_id': self.id,
                'group_id': self.group_id.id,
                'room_id': self.room_id.id,
                'time_start': self.time_start,
                'time_end': self.time_end,
                'state': 'open',
            })
            sheet._populate_lines()

        # Retourner l'action d'ouverture de la vue formulaire
        return {
            'name': f"Feuille de présence — {sheet.display_name}",
            'type': 'ir.actions.act_window',
            'res_model': 'winners.attendance.sheet',
            'view_mode': 'form',
            'res_id': sheet.id,
            'target': 'current',
        }

    @api.model
    def action_view_today_schedule(self):
        """
        Retourne l'action pour afficher uniquement les séances
        de l'emploi du temps correspondant à aujourd'hui.
        """
        local_tz = pytz.timezone('Africa/Algiers')
        now_local = datetime.now(local_tz)
        
        WEEKDAY_MAP = {
            0: 'monday',
            1: 'tuesday',
            2: 'wednesday',
            3: 'thursday',
            4: 'friday',
            5: 'saturday',
            6: 'sunday',
        }
        day_key = WEEKDAY_MAP.get(now_local.weekday(), 'monday')

        view_id = self.env.ref('winners_attendance.view_winners_schedule_today_tree').id

        return {
            'name': "Séances du jour",
            'type': 'ir.actions.act_window',
            'res_model': 'winners.schedule',
            'view_mode': 'tree',
            'views': [(view_id, 'tree')],
            'domain': [('day_of_week', '=', day_key), ('is_active', '=', True)],
            'context': {'create': False, 'delete': False, 'edit': False},
            'target': 'current',
        }

    def action_sync_zkteco_button(self):
        """
        Bouton manuel pour synchroniser immédiatement la pointeuse
        et afficher les nouveaux pointages sous forme de notification.
        """
        Processor = self.env['winners.attendance.processor']
        new_checkins = Processor.sync_now_and_get_results()
        
        if new_checkins:
            names_str = ", ".join(new_checkins)
            title = "Nouveaux pointages détectés"
            message = f"Les étudiants suivants ont été marqués présents : {names_str}"
            notif_type = "success"
        else:
            title = "Pointeuse synchronisée"
            message = "Aucun nouveau pointage détecté."
            notif_type = "info"
            
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'message': message,
                'type': notif_type,
                'sticky': False,
            }
        }
