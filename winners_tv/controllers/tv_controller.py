# pyrefly: ignore [missing-import]
import base64
import os
from datetime import datetime, timedelta

# pyrefly: ignore [missing-import]
from odoo import http, fields
# pyrefly: ignore [missing-import]
from odoo.http import request



class TVController(http.Controller):
    """Controller for Winners Academy TV display screen."""

    @http.route('/tv', type='http', auth='public', website=False, csrf=False)
    def tv_page(self, **kwargs):
        """Serve the standalone TV HTML page."""
        module_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        html_path = os.path.join(module_path, 'static', 'src', 'tv.html')
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        return request.make_response(
            html_content,
            headers=[('Content-Type', 'text/html; charset=utf-8')],
        )

    @http.route('/tv/data', type='http', auth='public', website=False, csrf=False)
    def tv_data(self, **kwargs):
        """Return JSON data for the TV display: schedule, last attendance, branch, time."""
        import json as json_mod

        now = fields.Datetime.now()
        today = fields.Date.today()

        # ── Day mapping ──
        day_map = {
            0: 'monday',
            1: 'tuesday',
            2: 'wednesday',
            3: 'thursday',
            4: 'friday',
            5: 'saturday',
            6: 'sunday',
        }

        # Determine timezone — TV is always in Algeria (UTC+1)
        from pytz import timezone, utc
        local_tz = timezone('Africa/Algiers')
        now_local = datetime.now(local_tz)
        current_day = day_map.get(now_local.weekday(), 'monday')

        # ── Subject labels ──
        subject_labels = {
            'arabic': 'العربية / Arabe',
            'french': 'الفرنسية / Français',
            'math': 'الرياضيات / Mathématiques',
            'science': 'العلوم / Sciences',
            'english': 'الإنجليزية / Anglais',
        }

        # ── Level labels ──
        level_labels = {
            'primaire_1': 'الابتدائي 1 / Primaire 1',
            'primaire_2': 'الابتدائي 2 / Primaire 2',
            'primaire_3': 'الابتدائي 3 / Primaire 3',
            'primaire_4': 'الابتدائي 4 / Primaire 4',
            'primaire_5': 'الابتدائي 5 / Primaire 5',
            'cem_1': 'متوسط 1 / CEM 1',
            'cem_2': 'متوسط 2 / CEM 2',
            'cem_3': 'متوسط 3 / CEM 3',
            'cem_4': 'متوسط 4 / CEM 4',
            'lycee_1': 'ثانوي 1 / Lycée 1',
            'lycee_2': 'ثانوي 2 / Lycée 2',
            'lycee_3': 'ثانوي 3 / Lycée 3',
        }

        # Current time as float for schedule comparisons (e.g. 14.5 = 14:30)
        current_float = now_local.hour + now_local.minute / 60.0

        # Today's start and end in local timezone converted to UTC for session query
        start_of_day_local = local_tz.localize(datetime(now_local.year, now_local.month, now_local.day, 0, 0, 0))
        end_of_day_local = local_tz.localize(datetime(now_local.year, now_local.month, now_local.day, 23, 59, 59))
        start_of_day_utc = start_of_day_local.astimezone(utc).replace(tzinfo=None)
        end_of_day_utc = end_of_day_local.astimezone(utc).replace(tzinfo=None)

        # ══════════════════════════════════════════
        # SOURCE 1: Recurring weekly schedule (winners.schedule)
        # ══════════════════════════════════════════
        Schedule = request.env['winners.schedule'].sudo()
        schedules = Schedule.search(
            [('day_of_week', '=', current_day), ('is_active', '=', True)],
            order='time_start asc',
        )

        # ══════════════════════════════════════════
        # SOURCE 2: Today's specific sessions (winners.session)
        # ══════════════════════════════════════════
        Session = request.env['winners.session'].sudo()
        sessions = Session.search(
            [
                ('date', '>=', start_of_day_utc),
                ('date', '<=', end_of_day_utc),
                ('status', '!=', 'cancelled'),
            ],
            order='date asc',
        )

        # Track which group_ids and times have a session today (to avoid duplicates)
        session_keys = set()
        schedule_data = []

        # ── Process sessions first (they take priority) ──
        for s in sessions:
            # Convert session date (UTC) to local timezone
            s_date_local = s.date.replace(tzinfo=utc).astimezone(local_tz)
            start_float = s_date_local.hour + s_date_local.minute / 60.0
            start_str = s_date_local.strftime('%H:%M')

            session_keys.add((s.group_id.id, start_str))

            # Calculate end time based on duration
            duration_h = s.duration_hours or 1.5
            s_end_local = s_date_local + timedelta(hours=duration_h)
            end_float = start_float + duration_h
            end_str = s_end_local.strftime('%H:%M')

            # Determine dynamic status
            if s.status == 'done' or current_float >= end_float:
                status = 'past'
            elif start_float <= current_float < end_float:
                status = 'current'
            else:
                status = 'upcoming'

            # Find room from schedule template
            schedule_rec = Schedule.search([
                ('group_id', '=', s.group_id.id),
                ('day_of_week', '=', current_day),
            ], limit=1)
            room_name = schedule_rec.room_id.name if schedule_rec else ''
            if not room_name:
                any_sched = Schedule.search([('group_id', '=', s.group_id.id)], limit=1)
                room_name = any_sched.room_id.name if any_sched else ''

            schedule_data.append({
                'group': s.group_id.name or '',
                'subject': subject_labels.get(s.group_id.subject, s.group_id.subject or ''),
                'teacher': s.group_id.teacher_id.name or '',
                'room': room_name,
                'time_start': start_str,
                'time_end': end_str,
                'status': status,
                '_sort_key': start_float,
                'source': 'session',
            })

        # ── Process schedule entries (only if no session exists for that group at that time) ──
        for sc in schedules:
            start_h = int(sc.time_start)
            start_m = int(round((sc.time_start - start_h) * 60))
            sched_start_str = f'{start_h:02d}:{start_m:02d}'

            if (sc.group_id.id, sched_start_str) in session_keys:
                continue  # Session already covers this group at this time

            end_h = int(sc.time_end)
            end_m = int(round((sc.time_end - end_h) * 60))

            if current_float >= sc.time_end:
                status = 'past'
            elif current_float >= sc.time_start and current_float < sc.time_end:
                status = 'current'
            else:
                status = 'upcoming'

            schedule_data.append({
                'group': sc.group_id.name or '',
                'subject': subject_labels.get(sc.group_id.subject, sc.group_id.subject or ''),
                'teacher': sc.teacher_id.name or '',
                'room': sc.room_id.name or '',
                'time_start': f'{start_h:02d}:{start_m:02d}',
                'time_end': f'{end_h:02d}:{end_m:02d}',
                'status': status,
                '_sort_key': sc.time_start,
                'source': 'schedule',
            })

        # ── Sort everything by start time ──
        schedule_data.sort(key=lambda x: x['_sort_key'])

        # Remove internal sort key before sending to frontend
        for item in schedule_data:
            item.pop('_sort_key', None)
            item.pop('source', None)

        # ── Recent attendances in the last 5 minutes (300 seconds) ──
        Attendance = request.env['winners.attendance.line'].sudo()
        cutoff = now - timedelta(minutes=5)
        recent_atts = Attendance.search(
            [
                ('sheet_date', '=', today),
                ('marked_at', '>=', cutoff),
                ('status', 'in', ['present', 'late']),
            ],
            order='marked_at asc',
        )

        recent_attendances = []
        for att in recent_atts:
            student = att.student_id
            photo_b64 = ''
            if student.photo:
                photo_b64 = student.photo.decode('utf-8') if isinstance(student.photo, bytes) else str(student.photo)

            enrollments = []
            for e in student.enrollment_ids:
                subject_name = subject_labels.get(e.group_id.subject, e.group_id.subject or '')
                enrollments.append({
                    'subject': subject_name,
                    'group': e.group_id.name or '',
                    'sessions_remaining': e.sessions_remaining,
                    'status': e.status,
                })

            recent_attendances.append({
                'id': att.id,
                'student_name': f'{student.first_name or ""} {student.name or ""}'.strip(),
                'photo': photo_b64,
                'level': level_labels.get(student.level, student.level or ''),
                'enrollments': enrollments,
                'timestamp': fields.Datetime.to_string(att.marked_at),
            })

        # ── Branch name (first active branch) ──
        Branch = request.env['winners.branch'].sudo()
        branch = Branch.search([('is_active', '=', True)], limit=1)
        branch_name = branch.name if branch else 'Winners Academy'

        # ── Build response ──
        data = {
            'schedule': schedule_data,
            'recent_attendances': recent_attendances,
            'branch_name': branch_name,
            'current_time': fields.Datetime.to_string(now),
        }

        response = request.make_response(
            json_mod.dumps(data, ensure_ascii=False),
            headers=[('Content-Type', 'application/json; charset=utf-8')],
        )
        return response
