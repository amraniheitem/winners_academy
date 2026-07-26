"""Test simulating real-time check-in to Odoo and verifying TV data endpoint."""
import sys
sys.path.append('C:/odoo17')
import odoo
import requests
import json

odoo.tools.config.parse_config(['-c', 'C:/odoo17/odoo.conf', '-d', 'odoo-test'])
registry = odoo.registry('odoo-test')

with registry.cursor() as cr:
    env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
    
    # 1. Find a student with zk_device_id
    students = env['winners.student'].search([('zk_device_id', '!=', False)], limit=3)
    print("Students with zk_device_id:")
    for s in students:
        print(f"  Student ID {s.id}: Name='{s.name}', zk_device_id={s.zk_device_id}")

    if not students:
        print("No students with zk_device_id found!")
        sys.exit(0)

    test_student = students[0]
    test_uid = test_student.zk_device_id

    # 2. Check if today has a sheet for this student's group
    today = odoo.fields.Date.today()
    sheets = env['winners.attendance.sheet'].search([('date', '=', today)])
    print(f"\nSheets for today ({today}): {len(sheets)}")
    for sh in sheets:
        print(f"  Sheet ID {sh.id}: Name='{sh.display_name}', Group='{sh.group_id.name}'")

    # 3. Simulate calling /winners/realtime_checkin HTTP POST
    url = "http://127.0.0.1:8069/winners/realtime_checkin"
    now_str = odoo.fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    payload = {
        'zk_device_id': str(test_uid),
        'timestamp': now_str
    }
    print(f"\nSimulating HTTP POST to {url} with payload: {payload}")
    
    try:
        res = requests.post(url, json=payload, timeout=5)
        print(f"Response HTTP {res.status_code}: {res.text}")
    except Exception as e:
        print(f"HTTP Request failed: {e}")

    # 4. Check TV data endpoint /tv/data
    try:
        tv_res = requests.get("http://127.0.0.1:8069/tv/data", timeout=5)
        tv_data = tv_res.json()
        print(f"\n/tv/data response contains {len(tv_data.get('recent_attendances', []))} recent attendances:")
        for att in tv_data.get('recent_attendances', []):
            print(f"  - Student: '{att.get('student_name')}', Level: '{att.get('level')}', Time: '{att.get('timestamp')}'")
    except Exception as e:
        print(f"TV data query failed: {e}")
