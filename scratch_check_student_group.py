"""Check HEITEM's groups and test attendance line creation."""
import sys
sys.path.append('C:/odoo17')
import odoo

odoo.tools.config.parse_config(['-c', 'C:/odoo17/odoo.conf', '-d', 'odoo-test'])
registry = odoo.registry('odoo-test')

with registry.cursor() as cr:
    env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
    student = env['winners.student'].browse(1) # HEITEM
    print(f"Student: {student.name} (zk_device_id={student.zk_device_id})")
    print("Enrollments:")
    for e in student.enrollment_ids:
        print(f"  - Group: {e.group_id.name} (ID {e.group_id.id}), Status: {e.status}")
    print("Direct groups:")
    for g in student.group_ids:
        print(f"  - Group: {g.name} (ID {g.id})")
