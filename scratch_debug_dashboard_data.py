import sys
import odoo

sys.stdout.reconfigure(encoding='utf-8')

config_file = r"C:\odoo17\odoo.conf"
odoo.tools.config.parse_config(["-c", config_file, "-d", "odoo-test"])

db_name = "odoo-test"
registry = odoo.registry(db_name)
with registry.cursor() as cr:
    env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})

    print("=== PAYMENTS IN DB ===")
    payments = env['winners.payment'].search_read([], ['id', 'student_id', 'amount', 'date', 'state'])
    for p in payments:
        print(p)

    print("\n=== STUDENTS IN DB ===")
    students = env['winners.student'].search_read([], ['id', 'name', 'status', 'create_date', 'sessions_remaining'])
    print(f"Total Students Count: {len(students)}")
    for s in students[:5]:
        print(s)

    print("\n=== SESSIONS TODAY / IN DB ===")
    sessions = env['winners.session'].search_read([], ['id', 'group_id', 'date', 'status'])
    print(f"Total Sessions Count: {len(sessions)}")
    for s in sessions[:5]:
        print(s)

    print("\n=== ATTENDANCES TODAY / IN DB ===")
    attendances = env['winners.attendance'].search_read([], ['id', 'student_id', 'date', 'status'])
    print(f"Total Attendances Count: {len(attendances)}")
    for a in attendances[:5]:
        print(a)
