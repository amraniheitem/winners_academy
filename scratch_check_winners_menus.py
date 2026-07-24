import odoo

config_file = r"C:\odoo17\odoo.conf"
odoo.tools.config.parse_config(["-c", config_file, "-d", "odoo-test"])

db_name = "odoo-test"
registry = odoo.registry(db_name)
with registry.cursor() as cr:
    cr.execute("SELECT id, name FROM ir_ui_menu WHERE name::text LIKE '%winners%' OR id IN (SELECT res_id FROM ir_model_data WHERE module LIKE 'winners_%' AND model = 'ir.ui.menu');")
    rows = cr.fetchall()
    print("ALL WINNERS MENUS:")
    for r in rows:
        print(r)

    print("\nALL WINNERS FIELDS:")
    cr.execute("SELECT id, name, field_description FROM ir_model_fields WHERE model LIKE 'winners.%';")
    fields = cr.fetchall()
    for f in fields:
        print(f)
