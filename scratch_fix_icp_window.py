"""Check ir_config_parameter for checkin_window_minutes and update to 45."""
import sys
sys.path.append('C:/odoo17')
import odoo

odoo.tools.config.parse_config(['-c', 'C:/odoo17/odoo.conf', '-d', 'odoo-test'])
registry = odoo.registry('odoo-test')

with registry.cursor() as cr:
    env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
    ICP = env['ir.config_parameter'].sudo()
    
    current_val = ICP.get_param('checkin_window_minutes')
    print(f"Current ir_config_parameter 'checkin_window_minutes': {current_val}")
    
    # Update to 45 minutes
    ICP.set_param('checkin_window_minutes', '45')
    print("Updated 'checkin_window_minutes' to 45 minutes in ir_config_parameter.")
