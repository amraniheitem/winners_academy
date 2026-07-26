"""Verify real-time checkin to /winners/realtime_checkin and TV response."""
import sys
sys.path.append('C:/odoo17')
import odoo
import requests

odoo.tools.config.parse_config(['-c', 'C:/odoo17/odoo.conf', '-d', 'odoo-test'])
registry = odoo.registry('odoo-test')

with registry.cursor() as cr:
    env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
    
    # Check current time
    now_str = odoo.fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"Current UTC time: {now_str}")
    
    # Simulate real-time checkin for HEITEM (zk_device_id = 2)
    url = "http://127.0.0.1:8069/winners/realtime_checkin"
    payload = {
        'zk_device_id': '2',
        'timestamp': now_str
    }
    print(f"Sending POST to {url}: {payload}")
    
    try:
        res = requests.post(url, json=payload, timeout=5)
        print(f"Response: {res.status_code} -> {res.text}")
    except Exception as e:
        print(f"POST failed: {e}")

    # Query TV data endpoint
    try:
        tv_res = requests.get("http://127.0.0.1:8069/tv/data", timeout=5)
        tv_data = tv_res.json()
        print(f"\n/tv/data recent attendances ({len(tv_data.get('recent_attendances', []))}):")
        for att in tv_data.get('recent_attendances', []):
            print(f"  - Student: {att.get('student_name')}, Level: {att.get('level')}, Time: {att.get('timestamp')}")
            print(f"    Enrollments: {att.get('enrollments')}")
    except Exception as e:
        print(f"TV query failed: {e}")
