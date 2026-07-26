"""Inspect cron jobs for attendance sheet generation."""
import sys
sys.path.append('C:/odoo17')
import odoo

odoo.tools.config.parse_config(['-c', 'C:/odoo17/odoo.conf', '-d', 'odoo-test'])
registry = odoo.registry('odoo-test')

with registry.cursor() as cr:
    env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
    crons = env['ir.cron'].search([])
    print("Total crons in DB:", len(crons))
    for c in crons:
        if 'attendance' in c.name.lower() or 'présence' in c.name.lower() or 'feuille' in c.name.lower() or 'generate' in c.name.lower() or 'daily' in c.name.lower():
            print(f"  Cron ID {c.id}: Name='{c.name}', Active={c.active}, NextCall={c.nextcall}, Interval={c.interval_number} {c.interval_type}, Code={c.code}")
