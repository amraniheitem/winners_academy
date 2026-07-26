"""Inspect why HEITEM is not matched to sheets today."""
import sys
sys.path.append('C:/odoo17')
import odoo

odoo.tools.config.parse_config(['-c', 'C:/odoo17/odoo.conf', '-d', 'odoo-test'])
registry = odoo.registry('odoo-test')

with registry.cursor() as cr:
    env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
    student = env['winners.student'].browse(1) # HEITEM
    today = odoo.fields.Date.today()
    
    today_sheets = env['winners.attendance.sheet'].search([('date', '=', today)])
    print(f"Today ({today}) total sheets: {len(today_sheets)}")
    
    for s in today_sheets:
        enrolled_students = s.group_id.enrollment_ids.filtered(lambda e: e.status == 'active').mapped('student_id.id')
        direct_students = s.group_id.student_ids.ids if hasattr(s.group_id, 'student_ids') else []
        is_in_group = (student.id in enrolled_students) or (student.id in direct_students)
        print(f"Sheet ID {s.id}: Group='{s.group_id.name}' (ID {s.group_id.id}), Time={s.time_start}-{s.time_end}, Is HEITEM in group? {is_in_group}")
        print(f"   Enrolled student IDs in group: {enrolled_students}")
