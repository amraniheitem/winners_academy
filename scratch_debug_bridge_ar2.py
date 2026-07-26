"""Debug: Show the exact arch returned by get_views in AR context to compare with FR."""
import sys, json
sys.path.append('C:/odoo17')
import odoo

odoo.tools.config.parse_config(['-c', 'C:/odoo17/odoo.conf', '-d', 'odoo-test'])
registry = odoo.registry('odoo-test')

with registry.cursor() as cr:
    env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
    view_ref = env.ref('winners_attendance.view_winners_attendance_sheet_form')

    # Get views in AR context
    env_ar = env(context={'lang': 'ar_001'})
    res_ar = env_ar['winners.attendance.sheet'].get_views(
        views=[(view_ref.id, 'form')],
        options={'toolbar': False}
    )

    arch_ar = res_ar['views']['form']['arch']
    fields_ar = res_ar['models']['winners.attendance.sheet']

    # Show the arch around bridge_status_html
    idx = arch_ar.find('bridge_status_html')
    if idx >= 0:
        start = max(0, idx - 100)
        end = min(len(arch_ar), idx + 200)
        print("=== AR arch around bridge_status_html ===")
        print(arch_ar[start:end])
    else:
        print("bridge_status_html NOT found in AR arch!")

    # Show the field definition
    if 'bridge_status_html' in fields_ar:
        print("\n=== bridge_status_html field definition (AR) ===")
        print(json.dumps(fields_ar['bridge_status_html'], indent=2, default=str, ensure_ascii=False))
    else:
        print("bridge_status_html NOT in AR fields dict!")

    # Check if there are any ir_ui_view_custom records (per-user customizations)
    cr.execute("""
        SELECT id, user_id, ref_id, arch 
        FROM ir_ui_view_custom 
        WHERE ref_id = %s
    """, (view_ref.id,))
    customs = cr.fetchall()
    print(f"\n=== ir_ui_view_custom for view {view_ref.id}: {len(customs)} records")
    for c in customs:
        print(f"  Custom ID {c[0]}, user_id {c[1]}, ref_id {c[2]}")

    # Check for any stale ir_translation entries (Odoo 17 uses arch_db JSONB but let's check)
    cr.execute("SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'ir_translation')")
    has_ir_translation = cr.fetchone()[0]
    print(f"\n=== Has ir_translation table: {has_ir_translation}")
    
    if has_ir_translation:
        cr.execute("""
            SELECT id, type, name, res_id, lang, src, value, state 
            FROM ir_translation 
            WHERE name LIKE '%%bridge_status%%'
        """)
        translations = cr.fetchall()
        print(f"Translations with bridge_status: {len(translations)}")
        for t in translations:
            print(f"  {t}")

    # Also check if the salary inherit view has proper AR translation
    cr.execute("""
        SELECT id, name, arch_db
        FROM ir_ui_view
        WHERE id = 1005
    """)
    salary_view = cr.fetchone()
    if salary_view:
        print(f"\n=== Salary inherit view {salary_view[0]}: {salary_view[1]}")
        arch_db = salary_view[2]
        if isinstance(arch_db, dict):
            print(f"  arch_db keys: {list(arch_db.keys())}")
            for lk, lv in arch_db.items():
                print(f"  lang={lk}: {lv[:200] if lv else 'EMPTY'}")
