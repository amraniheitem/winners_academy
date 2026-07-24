import sys
import odoo
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

config_file = r"C:\odoo17\odoo.conf"
odoo.tools.config.parse_config(["-c", config_file, "-d", "odoo-test"])

db_name = "odoo-test"
registry = odoo.registry(db_name)
with registry.cursor() as cr:
    env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})

    print("=== SESSIONS TODAY (2026-07-23) ===")
    sessions_today = env['winners.session'].search_read([('date', '>=', '2026-07-23 00:00:00'), ('date', '<=', '2026-07-23 23:59:59')], ['id', 'group_id', 'teacher_id', 'room_id', 'date', 'status'])
    print(f"Sessions count for 2026-07-23: {len(sessions_today)}")
    for s in sessions_today:
        print(s)

    print("\n=== SCHEDULE (EMPLOI DU TEMPS) FOR THURSDAY (JEUDI) ===")
    schedules_thursday = env['winners.schedule'].search_read([('day_of_week', '=', 'thursday')], ['id', 'group_id', 'teacher_id', 'room_id', 'time_start', 'time_end', 'branch_id'])
    print(f"Schedules count for Thursday: {len(schedules_thursday)}")
    for sc in schedules_thursday:
        print(sc)

    print("\n=== PAYMENTS (FOR RECENT PAYMENTS LIST & WEEK/MONTH/YEAR) ===")
    payments = env['winners.payment'].search_read([('state', '=', 'confirmed')], ['id', 'student_id', 'date', 'amount', 'state'], order='date desc, id desc')
    print(f"Total Confirmed Payments: {len(payments)}")
    for p in payments:
        print(p)
