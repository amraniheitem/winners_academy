"""Debug script: Check why bridge_status_html breaks in Arabic view."""
import sys
sys.path.append('C:/odoo17')
import odoo

odoo.tools.config.parse_config(['-c', 'C:/odoo17/odoo.conf', '-d', 'odoo-test'])
registry = odoo.registry('odoo-test')

with registry.cursor() as cr:
    env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})

    # 1. Check if the field exists in ir.model.fields
    cr.execute("""
        SELECT id, name, ttype, field_description
        FROM ir_model_fields
        WHERE model = 'winners.attendance.sheet' AND name = 'bridge_status_html'
    """)
    field_rows = cr.fetchall()
    print(f"=== ir.model.fields for bridge_status_html: {field_rows}")

    # 2. Check view arch_db (JSONB) for translations
    view_ref = env.ref('winners_attendance.view_winners_attendance_sheet_form')
    cr.execute("""
        SELECT id, name, arch_db
        FROM ir_ui_view
        WHERE id = %s
    """, (view_ref.id,))
    row = cr.fetchone()
    print(f"\n=== View ID {row[0]}, Name: {row[1]}")
    arch_db = row[2]
    if isinstance(arch_db, dict):
        print(f"arch_db is JSONB dict with keys: {list(arch_db.keys())}")
        for lang_key, arch_val in arch_db.items():
            has_field = 'bridge_status_html' in (arch_val or '')
            print(f"  lang={lang_key}: has bridge_status_html = {has_field}")
            if not has_field and lang_key != 'en_US':
                # Show a snippet around the sheet area
                if arch_val:
                    idx = arch_val.find('<sheet>')
                    if idx >= 0:
                        print(f"    Snippet after <sheet>: {arch_val[idx:idx+300]}")
    else:
        print(f"arch_db type: {type(arch_db)}")
        has_field = 'bridge_status_html' in str(arch_db or '')
        print(f"  has bridge_status_html = {has_field}")

    # 3. Check ALL inherited views for this model
    cr.execute("""
        SELECT v.id, v.name, v.inherit_id, v.arch_db
        FROM ir_ui_view v
        WHERE v.model = 'winners.attendance.sheet' AND v.type = 'form'
        ORDER BY v.id
    """)
    all_views = cr.fetchall()
    print(f"\n=== All form views for winners.attendance.sheet ({len(all_views)}):")
    for v_id, v_name, v_inherit_id, v_arch_db in all_views:
        print(f"  View {v_id}: {v_name} (inherit_id={v_inherit_id})")
        if isinstance(v_arch_db, dict):
            for lk, lv in v_arch_db.items():
                if lv and 'bridge_status_html' in lv:
                    print(f"    -> lang={lk} CONTAINS bridge_status_html")
        elif v_arch_db and 'bridge_status_html' in str(v_arch_db):
            print(f"    -> CONTAINS bridge_status_html")

    # 4. Simulate get_views in both languages
    print("\n=== get_views simulation ===")
    for lang in ['fr_FR', 'ar_001', 'ar']:
        try:
            env_lang = env(context={'lang': lang})
            res = env_lang['winners.attendance.sheet'].get_views(
                views=[(view_ref.id, 'form')],
                options={'toolbar': False}
            )
            fields_dict = res.get('models', {}).get('winners.attendance.sheet', {})
            has_field = 'bridge_status_html' in fields_dict
            arch = res.get('views', {}).get('form', {}).get('arch', '')
            arch_has = 'bridge_status_html' in arch
            print(f"  {lang}: fields_dict has bridge_status_html = {has_field}, arch has = {arch_has}")
            if not has_field:
                # Show what fields are near it alphabetically
                sorted_fields = sorted(fields_dict.keys())
                b_fields = [f for f in sorted_fields if f.startswith('b')]
                print(f"    Fields starting with 'b': {b_fields}")
        except Exception as e:
            print(f"  {lang}: ERROR - {e}")
