"""Run _generate_daily_sheets for today and print created sheets."""
import sys
sys.path.append('C:/odoo17')
import odoo

odoo.tools.config.parse_config(['-c', 'C:/odoo17/odoo.conf', '-d', 'odoo-test'])
registry = odoo.registry('odoo-test')

with registry.cursor() as cr:
    env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
    created = env['winners.attendance.sheet']._generate_daily_sheets()
    print(f"Generated {len(created)} sheets for today:")
    for s in created:
        print(f"  Created Sheet ID {s.id}: {s.display_name} (Group: {s.group_id.name}, Room: {s.room_id.name})")
