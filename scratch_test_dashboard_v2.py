import sys
import odoo
from datetime import datetime, timedelta

sys.stdout.reconfigure(encoding='utf-8')

config_file = r"C:\odoo17\odoo.conf"
odoo.tools.config.parse_config(["-c", config_file, "-d", "odoo-test"])

db_name = "odoo-test"
registry = odoo.registry(db_name)
with registry.cursor() as cr:
    env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})

    now = datetime.now()
    today_str = now.strftime('%Y-%m-%d')
    days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    current_day = days[now.weekday()]

    print(f"Today: {today_str}, Day of Week: {current_day}")

    # 1. Sessions for today
    sessions_today_count = env['winners.session'].search_count([('date', '>=', today_str + ' 00:00:00'), ('date', '<=', today_str + ' 23:59:59')])
    schedules_today_count = env['winners.schedule'].search_count([('day_of_week', '=', current_day), ('is_active', '=', True)])
    print(f"Sessions created for today: {sessions_today_count}")
    print(f"Schedules in timetable for {current_day}: {schedules_today_count}")

    # 2. Payments (Week, Month, Year)
    payments = env['winners.payment'].search_read([('state', '=', 'confirmed')], ['id', 'student_id', 'date', 'amount'])
    
    # Calculate week, month, year start
    week_start = (now - timedelta(days=now.weekday())).strftime('%Y-%m-%d')
    month_start = now.strftime('%Y-%m-01')
    year_start = now.strftime('%Y-01-01')

    rev_week = sum(p['amount'] for p in payments if p['date'] and str(p['date']) >= week_start)
    rev_month = sum(p['amount'] for p in payments if p['date'] and str(p['date']) >= month_start)
    rev_year = sum(p['amount'] for p in payments if p['date'] and str(p['date']) >= year_start)
    total_rev = sum(p['amount'] for p in payments)

    print(f"\nRevenue Week (from {week_start}): {rev_week} DA")
    print(f"Revenue Month (from {month_start}): {rev_month} DA")
    print(f"Revenue Year (from {year_start}): {rev_year} DA")
    print(f"Total All-Time Revenue: {total_rev} DA")

    # 3. Timetable items for table display
    schedules_list = env['winners.schedule'].search_read([('day_of_week', '=', current_day)], ['id', 'group_id', 'teacher_id', 'room_id', 'time_start', 'time_end'], limit=5)
    print(f"\nSchedule Entries for {current_day}:")
    for sc in schedules_list:
        print(sc)
