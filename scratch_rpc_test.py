import sys
sys.path.append('C:/odoo17')
import odoo

odoo.tools.config.parse_config(['-c', 'C:/odoo17/odoo.conf', '-d', 'odoo-test'])
registry = odoo.registry('odoo-test')

with registry.cursor() as cr:
    env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
    
    # 1. French context
    env_fr = env(context={'lang': 'fr_FR'})
    res_fr = env_fr['winners.attendance.sheet'].get_views(
        views=[(env.ref('winners_attendance.view_winners_attendance_sheet_form').id, 'form')],
        options={'toolbar': True}
    )
    
    # 2. Arabic (ar_001) context
    env_ar1 = env(context={'lang': 'ar_001'})
    res_ar1 = env_ar1['winners.attendance.sheet'].get_views(
        views=[(env.ref('winners_attendance.view_winners_attendance_sheet_form').id, 'form')],
        options={'toolbar': True}
    )

    # 3. Arabic (ar) context
    env_ar = env(context={'lang': 'ar'})
    res_ar = env_ar['winners.attendance.sheet'].get_views(
        views=[(env.ref('winners_attendance.view_winners_attendance_sheet_form').id, 'form')],
        options={'toolbar': True}
    )

    fields_fr = res_fr['models']['winners.attendance.sheet'].keys()
    fields_ar1 = res_ar1['models']['winners.attendance.sheet'].keys()
    fields_ar = res_ar['models']['winners.attendance.sheet'].keys()

    print("FR fields in models dict:", 'bridge_status_html' in fields_fr)
    print("ar_001 fields in models dict:", 'bridge_status_html' in fields_ar1)
    print("ar fields in models dict:", 'bridge_status_html' in fields_ar)

    # Check if there is an ir.ui.view view translation or COW view in DB for Arabic
    cr.execute("SELECT id, name, lang, arch_db FROM ir_ui_view WHERE model = 'winners.attendance.sheet'")
    db_views = cr.fetchall()
    print(f"Total ir_ui_view rows in DB: {len(db_views)}")
    for v_id, v_name, v_lang, v_arch in db_views:
        print(f"DB View ID {v_id}, Name {v_name}, Lang {v_lang}")
