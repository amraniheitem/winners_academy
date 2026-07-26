"""Test simulating checkin at 16:50 (within 10 mins of 17:00 class)."""
import sys
sys.path.append('C:/odoo17')
import odoo
import requests

odoo.tools.config.parse_config(['-c', 'C:/odoo17/odoo.conf', '-d', 'odoo-test'])
registry = odoo.registry('odoo-test')

with registry.cursor() as cr:
    env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
    
    # Simulate checkin at 16:55 (5 mins before 17:00 sheet)
    now_str = odoo.fields.Datetime.now().strftime('%Y-%m-%d 16:55:00')
    url = "http://127.0.0.1:8069/winners/realtime_checkin"
    payload = {
        'zk_device_id': '2', # HEITEM
        'timestamp': now_str
    }
    print(f"Simulating HTTP POST to {url} with payload: {payload}")
    
    res = requests.post(url, json=payload, timeout=5)
    print(f"Response HTTP {res.status_code}: {res.text}")

    # Query TV data
    tv_res = requests.get("http://127.0.0.1:8069/tv/data", timeout=5)
    tv_data = tv_res.json()
    print(f"\n/tv/data response contains {len(tv_data.get('recent_attendances', []))} recent attendances:")
    for att in tv_data.get('recent_attendances', []):
        print(f"  - Student: '{att.get('student_name')}', Level: '{att.get('level')}', Time: '{att.get('timestamp')}'")
