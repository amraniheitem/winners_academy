import sys
sys.path.append('C:/odoo17')
import odoo

odoo.tools.config.parse_config(['-c', 'C:/odoo17/odoo.conf', '-d', 'odoo-test'])
registry = odoo.registry('odoo-test')

with registry.cursor() as cr:
    cr.execute("SELECT id, user_id, ref_id, arch FROM ir_ui_view_custom")
    custom_views = cr.fetchall()
    print(f"Found {len(custom_views)} ir_ui_view_custom rows:")
    for cid, uid, ref_id, arch in custom_views:
        print(f"Custom View ID: {cid}, User ID: {uid}, Ref View ID: {ref_id}")
        print("Arch excerpt:", arch[:200])
