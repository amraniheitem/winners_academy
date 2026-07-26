"""Debug process_checkin step by step for HEITEM."""
import sys
sys.path.append('C:/odoo17')
import odoo
from datetime import datetime

odoo.tools.config.parse_config(['-c', 'C:/odoo17/odoo.conf', '-d', 'odoo-test'])
registry = odoo.registry('odoo-test')

with registry.cursor() as cr:
    env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
    Processor = env['winners.attendance.processor']
    
    zk_device_id = 2 # HEITEM
    timestamp = datetime.now()
    
    window_minutes = Processor._get_checkin_window_minutes()
    print(f"window_minutes: {window_minutes}")
    
    local_timestamp = timestamp
    checkin_date = local_timestamp.date()
    checkin_float = local_timestamp.hour + local_timestamp.minute / 60.0
    window_float = window_minutes / 60.0
    
    print(f"checkin_date: {checkin_date}, checkin_float: {checkin_float:.4f}, window_float: {window_float:.4f}")
    
    today_sheets = env['winners.attendance.sheet'].search([
        ('date', '=', checkin_date),
        ('state', '!=', 'closed'),
    ])
    print(f"today_sheets total: {len(today_sheets)}")
    
    student = env['winners.student'].search([('zk_device_id', '=', zk_device_id)], limit=1)
    print(f"Student: {student.name} (ID {student.id})")
    
    for sheet in today_sheets:
        active_enrollment = sheet.group_id.enrollment_ids.filtered(
            lambda enrollment: enrollment.student_id.id == student.id
            and enrollment.status == 'active'
        )
        is_in_group = bool(active_enrollment) or (student.id in sheet.group_id.student_ids.ids)
        time_start = sheet.time_start
        time_end = sheet.time_end
        
        diff = abs(checkin_float - time_start)
        in_window = diff <= window_float or (time_start <= checkin_float <= time_end)
        
        print(f"  Sheet {sheet.id} ('{sheet.display_name}'): is_in_group={is_in_group}, start={time_start}, end={time_end}, diff={diff:.4f}, in_window={in_window}")
