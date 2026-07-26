"""Trigger ZK sync in Odoo to update status banner and sync recent punches."""
import sys
sys.path.append('C:/odoo17')
import odoo

odoo.tools.config.parse_config(['-c', 'C:/odoo17/odoo.conf', '-d', 'odoo-test'])
registry = odoo.registry('odoo-test')

with registry.cursor() as cr:
    env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
    Processor = env['winners.attendance.processor']
    
    print("Executing ZK sync from Odoo...")
    new_checkins = Processor.sync_now_and_get_results()
    print("New checkins:", new_checkins)
    
    report = Processor.get_last_sync_report()
    print("Sync report:", report)
    
    status = Processor.get_bridge_status()
    print("Updated Bridge Status:", status)
