import sys
sys.path.append('C:/odoo17')
import odoo

odoo.tools.config.parse_config(['-c', 'C:/odoo17/odoo.conf', '-d', 'odoo-test'])
registry = odoo.registry('odoo-test')

with registry.cursor() as cr:
    env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
    views = env['ir.ui.view'].search([('model', '=', 'winners.attendance.sheet'), ('type', '=', 'form')])
    print(f"Found {len(views)} form views:")
    for v in views:
        print(f"--- View ID: {v.id}, Name: {v.name}, xml_id: {v.xml_id}, inherit_id: {v.inherit_id.id if v.inherit_id else None} ---")
        arch_fr = env['winners.attendance.sheet'].with_context(lang='fr_FR').get_views([(v.id, 'form')])['views']['form']['arch']
        arch_ar = env['winners.attendance.sheet'].with_context(lang='ar_001').get_views([(v.id, 'form')])['views']['form']['arch']
        
        has_field_fr = 'bridge_status_html' in arch_fr
        has_field_ar = 'bridge_status_html' in arch_ar
        print(f"Contains bridge_status_html -> FR: {has_field_fr}, AR: {has_field_ar}")
        if not has_field_ar:
            print("AR Arch excerpt:", arch_ar[:300])
