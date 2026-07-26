"""Test realtime POST with unique timestamp."""
import sys
sys.path.append('C:/odoo17')
import odoo
import requests
from datetime import datetime

odoo.tools.config.parse_config(['-c', 'C:/odoo17/odoo.conf', '-d', 'odoo-test'])
registry = odoo.registry('odoo-test')

with registry.cursor() as cr:
    env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
    
    # Use exact current time formatted as YYYY-MM-DD HH:MM:SS
    unique_ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    url = "http://127.0.0.1:8069/winners/realtime_checkin"
    payload = {
        'zk_device_id': '2', # HEITEM
        'timestamp': unique_ts
    }
    print(f"Sending POST to {url} with unique timestamp {unique_ts}...")
    res = requests.post(url, json=payload, timeout=5)
    print(f"Response HTTP {res.status_code}: {res.text}")

    # Query TV data
    tv_res = requests.get("http://127.0.0.1:8069/tv/data", timeout=5)
    tv_data = tv_res.json()
    print(f"\n/tv/data recent attendances ({len(tv_data.get('recent_attendances', []))}):")
    for att in tv_data.get('recent_attendances', []):
        print(f"  - Student: {att.get('student_name')}, Level: {att.get('level')}, Time: {att.get('timestamp')}")
