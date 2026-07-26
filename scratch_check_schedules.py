"""Check active schedules and why _generate_daily_sheets creates or doesn't create sheets."""
import sys
sys.path.append('C:/odoo17')
import odoo

odoo.tools.config.parse_config(['-c', 'C:/odoo17/odoo.conf', '-d', 'odoo-test'])
registry = odoo.registry('odoo-test')

with registry.cursor() as cr:
    env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})

    today = odoo.fields.Date.today()
    weekday_idx = today.weekday()
    WEEKDAY_MAP = {0: 'monday', 1: 'tuesday', 2: 'wednesday', 3: 'thursday', 4: 'friday', 5: 'saturday', 6: 'sunday'}
    day_key = WEEKDAY_MAP[weekday_idx]
    print(f"Today is {today}, weekday index: {weekday_idx} -> key: '{day_key}'")

    # 1. Inspect all schedules in DB
    schedules_all = env['winners.schedule'].search([])
    print(f"\nTotal winners.schedule in DB: {len(schedules_all)}")
    for s in schedules_all:
        print(f"  ID {s.id}: Group='{s.group_id.name}', Day='{s.day_of_week}', Active={s.is_active}, Time={s.time_start}-{s.time_end}, Room='{s.room_id.name}'")

    # 2. Inspect schedules for today
    schedules_today = env['winners.schedule'].search([('day_of_week', '=', day_key), ('is_active', '=', True)])
    print(f"\nActive schedules matching today ('{day_key}'): {len(schedules_today)}")

    # 3. Inspect existing attendance sheets for today
    sheets_today = env['winners.attendance.sheet'].search([('date', '=', today)])
    print(f"\nExisting attendance sheets for today ({today}): {len(sheets_today)}")
    for sh in sheets_today:
        print(f"  Sheet ID {sh.id}: Name='{sh.display_name}', Schedule_ID={sh.schedule_id.id}, Group='{sh.group_id.name}', Time={sh.time_start}-{sh.time_end}")

    # 4. Check if cron or auto-generation is triggered or if there are day_of_week mismatches
    cr.execute("SELECT DISTINCT day_of_week FROM winners_schedule")
    distinct_days = cr.fetchall()
    print(f"\nDistinct day_of_week values in winners_schedule table: {distinct_days}")
