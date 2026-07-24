import odoo
from odoo import api, SUPERUSER_ID

config_file = r"C:\odoo17\odoo.conf"
odoo.tools.config.parse_config(["-c", config_file, "-d", "odoo-test"])

db_name = "odoo-test"
registry = odoo.registry(db_name)
with registry.cursor() as cr:
    cr.execute("SELECT id, name FROM ir_ui_menu WHERE name::text LIKE '%Personnes%' OR name::text LIKE '%Salaires%' LIMIT 5;")
    rows = cr.fetchall()
    print("ir_ui_menu rows:", rows)

    cr.execute("SELECT id, field_description FROM ir_model_fields WHERE field_description::text LIKE '%Matière%' OR field_description::text LIKE '%Salaire%' LIMIT 5;")
    rows_f = cr.fetchall()
    print("ir_model_fields rows:", rows_f)
