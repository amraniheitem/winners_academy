# pyrefly: ignore [missing-import]
from odoo import api, fields, models
from datetime import datetime
import pytz


WEEKDAY_MAP = {
    0: 'monday',
    1: 'tuesday',
    2: 'wednesday',
    3: 'thursday',
    4: 'friday',
    5: 'saturday',
    6: 'sunday',
}


class WinnersRoom(models.Model):
    _name = "winners.room"
    _description = "Salle Winners"

    name = fields.Char(
        string="Nom de la salle",
        required=True,
    )
    capacity = fields.Integer(
        string="Capacité (places)",
        default=20,
    )
    branch_id = fields.Many2one(
        comodel_name="winners.branch",
        string="Branche",
        required=True,
        default=lambda self: self.env.user.branch_id,
    )
    floor = fields.Char(
        string="Étage",
    )
    equipment = fields.Text(
        string="Équipements",
    )
    is_active = fields.Boolean(
        string="Disponible",
        default=True,
    )

    @api.model
    def _float_to_time_label(self, hour_float):
        hours = int(hour_float)
        minutes = int(round((hour_float - hours) * 60))
        return f"{hours:02d}:{minutes:02d}"

    @api.model
    def _local_datetime_bounds(self, date_value, time_start, time_end):
        tz_name = self.env.user.tz or self.env.context.get('tz') or 'Africa/Algiers'
        try:
            local_tz = pytz.timezone(tz_name)
        except Exception:
            local_tz = pytz.timezone('Africa/Algiers')

        start_hour = int(time_start)
        start_minute = int(round((time_start - start_hour) * 60))
        end_hour = int(time_end)
        end_minute = int(round((time_end - end_hour) * 60))

        local_start = local_tz.localize(
            datetime(date_value.year, date_value.month, date_value.day, start_hour, start_minute)
        )
        local_end = local_tz.localize(
            datetime(date_value.year, date_value.month, date_value.day, end_hour, end_minute)
        )
        return (
            local_start.astimezone(pytz.utc).replace(tzinfo=None),
            local_end.astimezone(pytz.utc).replace(tzinfo=None),
        )

    def check_available(self, date_value, time_start, time_end, ignore_model=None, ignore_id=None):
        self.ensure_one()
        return self._check_room_availability(
            self,
            date_value,
            time_start,
            time_end,
            exclude_id=ignore_id,
            exclude_model=ignore_model,
        )

    @api.model
    def get_available_rooms(
        self, date_or_day, time_start, time_end, branch_id=None,
        exclude_id=None, exclude_model=None, exclude_schedule_id=None
    ):
        """
        Retourne les salles actives disponibles pour un créneau donné.
        """
        domain = [('is_active', '=', True)]
        if branch_id:
            domain.append(('branch_id', '=', branch_id))

        all_rooms = self.search(domain)
        available_rooms = self.browse()
        for r in all_rooms:
            is_avail, _ = self._check_room_availability(
                r, date_or_day, time_start, time_end,
                exclude_id=exclude_id, exclude_model=exclude_model,
                exclude_schedule_id=exclude_schedule_id,
                suggest_rooms=False,
            )
            if is_avail:
                available_rooms |= r
        return available_rooms

    @api.model
    def _check_room_availability(
        self, room_id, date_or_day, time_start, time_end,
        exclude_id=None, exclude_model=None, exclude_schedule_id=None, exclude_group_id=None,
        check_schedules=True, check_sheets=True, check_sessions=True,
        suggest_rooms=True
    ):
        if not room_id:
            return True, ""
        Room = self.env['winners.room']
        room = Room.browse(room_id) if isinstance(room_id, int) else room_id
        if not room.is_active:
            return False, f"La salle {room.name} est inactive."

        if time_end <= time_start:
            return False, "L'heure de fin doit être supérieure à l'heure de début."

        # Déterminer le jour de la semaine et la date
        day_key = None
        date_val = None
        if isinstance(date_or_day, str) and date_or_day in WEEKDAY_MAP.values():
            day_key = date_or_day
        else:
            date_val = fields.Date.from_string(date_or_day) if isinstance(date_or_day, str) else date_or_day
            if date_val:
                day_key = WEEKDAY_MAP.get(date_val.weekday())

        def _format_suggestions():
            if not suggest_rooms:
                return ""
            branch_id = room.branch_id.id if room.branch_id else None
            avail = self.get_available_rooms(
                date_or_day, time_start, time_end, branch_id=branch_id,
                exclude_id=exclude_id, exclude_model=exclude_model,
                exclude_schedule_id=exclude_schedule_id,
            )
            other_avail = avail.filtered(lambda r: r.id != room.id)
            if other_avail:
                names = ", ".join(other_avail.mapped('name'))
                return f"\n\n💡 Salles libres à ce créneau dans cette branche : {names}."
            else:
                return "\n\n⚠️ Aucune autre salle n'est disponible à ce créneau."

        # 1. Vérification de l'emploi du temps (schedule)
        if check_schedules and day_key and 'winners.schedule' in self.env.registry:
            schedule_domain = [
                ('room_id', '=', room.id),
                ('day_of_week', '=', day_key),
                ('is_active', '=', True),
                ('time_start', '<', time_end),
                ('time_end', '>', time_start),
            ]
            if exclude_model == 'winners.schedule' and exclude_id:
                schedule_domain.append(('id', '!=', exclude_id))
            if exclude_schedule_id:
                schedule_domain.append(('id', '!=', exclude_schedule_id))
            if exclude_group_id:
                schedule_domain.append(('group_id', '!=', exclude_group_id))
            
            overlap_schedule = self.env['winners.schedule'].search(schedule_domain, limit=1)
            if overlap_schedule:
                start_h = int(overlap_schedule.time_start)
                start_m = int(round((overlap_schedule.time_start - start_h) * 60))
                end_h = int(overlap_schedule.time_end)
                end_m = int(round((overlap_schedule.time_end - end_h) * 60))
                day_label = dict(self.env['winners.schedule']._fields['day_of_week'].selection or []).get(day_key, day_key)
                sugg = _format_suggestions()
                return False, (
                    f"La salle « {room.name} » est déjà réservée par l'emploi du temps du groupe "
                    f"« {overlap_schedule.group_id.name} » de {start_h:02d}:{start_m:02d} à {end_h:02d}:{end_m:02d} le {day_label}.{sugg}"
                )

        # 2. Vérification des séances ponctuelles (winners.session)
        if check_sessions and date_val and 'winners.session' in self.env.registry:
            start_dt = fields.Datetime.from_string(f"{date_val} 00:00:00")
            end_dt = fields.Datetime.from_string(f"{date_val} 23:59:59")
            session_domain = [
                ('room_id', '=', room.id),
                ('status', '!=', 'cancelled'),
                ('date', '>=', start_dt),
                ('date', '<=', end_dt),
            ]
            if exclude_model == 'winners.session' and exclude_id:
                session_domain.append(('id', '!=', exclude_id))
            if exclude_group_id:
                session_domain.append(('group_id', '!=', exclude_group_id))

            sessions = self.env['winners.session'].search(session_domain)
            for sess in sessions:
                if not sess.date:
                    continue
                sess_time = fields.Datetime.context_timestamp(sess, sess.date)
                sess_start = sess_time.hour + sess_time.minute / 60.0
                sess_end = sess_start + (sess.duration_hours or 1.5)

                if max(time_start, sess_start) < min(time_end, sess_end):
                    s_h, s_m = int(sess_start), int(round((sess_start - int(sess_start)) * 60))
                    e_h, e_m = int(sess_end), int(round((sess_end - int(sess_end)) * 60))
                    sugg = _format_suggestions()
                    return False, (
                        f"La salle « {room.name} » est déjà occupée par la séance "
                        f"du groupe « {sess.group_id.name} » de {s_h:02d}:{s_m:02d} à {e_h:02d}:{e_m:02d} le {date_val}.{sugg}"
                    )

        # 3. Vérification des feuilles de présence (sheet)
        if check_sheets and 'winners.attendance.sheet' in self.env.registry:
            sheet_domain = [
                ('room_id', '=', room.id),
                ('state', '!=', 'closed'),
                ('time_start', '<', time_end),
                ('time_end', '>', time_start),
            ]
            if date_val:
                sheet_domain.append(('date', '=', date_val))
            if exclude_model == 'winners.attendance.sheet' and exclude_id:
                sheet_domain.append(('id', '!=', exclude_id))
            if exclude_group_id:
                sheet_domain.append(('group_id', '!=', exclude_group_id))

            overlap_sheet = self.env['winners.attendance.sheet'].search(sheet_domain)
            if not date_val and day_key:
                overlap_sheet = overlap_sheet.filtered(
                    lambda sheet: sheet.date and WEEKDAY_MAP.get(sheet.date.weekday()) == day_key
                )
            overlap_sheet = overlap_sheet[:1]
            if overlap_sheet:
                start_h = int(overlap_sheet.time_start)
                start_m = int(round((overlap_sheet.time_start - start_h) * 60))
                end_h = int(overlap_sheet.time_end)
                end_m = int(round((overlap_sheet.time_end - end_h) * 60))
                sugg = _format_suggestions()
                return False, (
                    f"La salle « {room.name} » est déjà occupée par la feuille de présence "
                    f"« {overlap_sheet.display_name} » ({start_h:02d}:{start_m:02d} à {end_h:02d}:{end_m:02d}) !{sugg}"
                )

        return True, "Salle disponible."
