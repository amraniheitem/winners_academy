import sys
import json
import odoo

sys.stdout.reconfigure(encoding='utf-8')

config_file = r"C:\odoo17\odoo.conf"
odoo.tools.config.parse_config(["-c", config_file, "-d", "odoo-test"])

db_name = "odoo-test"
registry = odoo.registry(db_name)
with registry.cursor() as cr:
    print("=== DUMPING ALL MENUS IN ODOO ===")
    cr.execute("SELECT id, name FROM ir_ui_menu WHERE id IN (SELECT res_id FROM ir_model_data WHERE module LIKE 'winners_%' AND model = 'ir.ui.menu') OR name::text LIKE '%winners%';")
    menus = cr.fetchall()
    for m in menus:
        print(f"MENU {m[0]}: {m[1]}")

    print("\n=== DUMPING ALL WINNERS ACTIONS ===")
    cr.execute("SELECT id, name FROM ir_act_window WHERE id IN (SELECT res_id FROM ir_model_data WHERE module LIKE 'winners_%' AND model = 'ir.actions.act_window');")
    actions = cr.fetchall()
    for a in actions:
        print(f"ACTION {a[0]}: {a[1]}")

    print("\n=== DUMPING ALL WINNERS FIELDS ===")
    cr.execute("SELECT id, name, field_description FROM ir_model_fields WHERE model LIKE 'winners.%';")
    fields = cr.fetchall()
    for f in fields:
        print(f"FIELD {f[0]} ({f[1]}): {f[2]}")

    print("\n=== DUMPING ALL WINNERS SELECTIONS ===")
    cr.execute("SELECT id, name FROM ir_model_fields_selection WHERE field_id IN (SELECT id FROM ir_model_fields WHERE model LIKE 'winners.%');")
    sels = cr.fetchall()
    for s in sels:
        print(f"SELECTION {s[0]}: {s[1]}")
