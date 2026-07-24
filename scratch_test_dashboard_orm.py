import sys
import odoo

sys.stdout.reconfigure(encoding='utf-8')

config_file = r"C:\odoo17\odoo.conf"
odoo.tools.config.parse_config(["-c", config_file, "-d", "odoo-test"])

db_name = "odoo-test"
registry = odoo.registry(db_name)
with registry.cursor() as cr:
    env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})

    print("=== 1. STUDENTS ===")
    total_students = env['winners.student'].search_count([])
    active_students = env['winners.student'].search_count([('status', '=', 'active')])
    expired_students = env['winners.student'].search_count([('status', '=', 'expired')])
    alert_students = env['winners.student'].search_count([('sessions_remaining', '<=', 2), ('sessions_remaining', '>', 0)])
    print(f"Total: {total_students}, Active: {active_students}, Expired: {expired_students}, Alert: {alert_students}")

    print("\n=== 2. PAYMENTS ===")
    payments = env['winners.payment'].search_read([('state', '=', 'confirmed')], ['id', 'student_id', 'amount', 'date', 'state'])
    total_revenue = sum(p['amount'] for p in payments)
    print(f"Confirmed Payments Count: {len(payments)}, Total Revenue: {total_revenue} DA")
    for p in payments:
        print(f"  - Payment #{p['id']}: Student={p['student_id'][1] if p['student_id'] else 'N/A'}, Amount={p['amount']}, Date={p['date']}")

    print("\n=== 3. TEACHERS & GROUPS ===")
    total_teachers = env['winners.teacher'].search_count([])
    total_groups = env['winners.group'].search_count([])
    print(f"Teachers: {total_teachers}, Groups: {total_groups}")

    print("\n=== 4. ROOMS & SESSIONS ===")
    total_rooms = env['winners.room'].search_count([])
    total_sessions = env['winners.session'].search_count([])
    print(f"Rooms: {total_rooms}, Total Sessions: {total_sessions}")

    print("\n=== 5. ATTENDANCE SHEETS & LINES ===")
    sheets_count = env['winners.attendance.sheet'].search_count([])
    lines_count = env['winners.attendance.line'].search_count([])
    presents_count = env['winners.attendance.line'].search_count([('status', 'in', ['present', 'late'])])
    absents_count = env['winners.attendance.line'].search_count([('status', '=', 'absent')])
    print(f"Sheets: {sheets_count}, Attendance Lines: {lines_count}, Presents: {presents_count}, Absents: {absents_count}")
