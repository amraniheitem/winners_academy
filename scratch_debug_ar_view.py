import sys
sys.path.append('C:/odoo17')
import odoo

odoo.tools.config.parse_config(['-c', 'C:/odoo17/odoo.conf', '-d', 'odoo-test'])
registry = odoo.registry('odoo-test')

with registry.cursor() as cr:
    env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
    Sheet_fr = env['winners.attendance.sheet'].with_context(lang='fr_FR')
    Sheet_ar = env['winners.attendance.sheet'].with_context(lang='ar_001')
    
    v_fr = Sheet_fr.get_views([(env.ref('winners_attendance.view_winners_attendance_sheet_form').id, 'form')])
    v_ar = Sheet_ar.get_views([(env.ref('winners_attendance.view_winners_attendance_sheet_form').id, 'form')])
    
    print("FR view models keys:", v_fr.get('models', {}).get('winners.attendance.sheet', {}).keys())
    print("FR arch contains bridge_status_html:", 'bridge_status_html' in v_fr['views']['form']['arch'])
    print("AR arch contains bridge_status_html:", 'bridge_status_html' in v_ar['views']['form']['arch'])
    print("FR models fields contains bridge_status_html:", 'bridge_status_html' in v_fr.get('models', {}).get('winners.attendance.sheet', {}))
    print("AR models fields contains bridge_status_html:", 'bridge_status_html' in v_ar.get('models', {}).get('winners.attendance.sheet', {}))
