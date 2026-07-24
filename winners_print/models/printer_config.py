# -*- coding: utf-8 -*-
from datetime import date
from odoo import _, api, fields, models
from odoo.exceptions import UserError
from . import printer_service


class WinnersPrinterConfig(models.Model):
    _name = 'winners.printer.config'
    _description = 'Configuration Imprimante Thermique'

    name = fields.Char(
        string='Nom de la configuration',
        required=True,
        default='Imprimante Principale'
    )
    vendor_id = fields.Char(
        string='Vendor ID (HEX)',
        required=True,
        default='0x0483',
        help='ex: 0x0483'
    )
    product_id = fields.Char(
        string='Product ID (HEX)',
        required=True,
        default='0x5743',
        help='ex: 0x5743'
    )
    academy_name = fields.Char(
        string="Nom de l'académie",
        required=True,
        default='WINNERS ACADEMY'
    )
    branch_name = fields.Char(
        string='Nom de la branche',
        default='Branche Principale'
    )
    active = fields.Boolean(
        string='Actif',
        default=True
    )
    is_default = fields.Boolean(
        string='Par défaut',
        default=True
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('is_default'):
                self.search([('is_default', '=', True)]).write({'is_default': False})
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('is_default'):
            self.search([('is_default', '=', True)]).write({'is_default': False})
        return super().write(vals)

    def action_test_impression(self):
        """Imprime un ticket de test sur l'imprimante thermique USB."""
        self.ensure_one()

        try:
            v_id = int(self.vendor_id, 16)
            p_id = int(self.product_id, 16)
        except (ValueError, TypeError):
            raise UserError(_("Les identifiants VendorID et ProductID doivent être au format hexadécimal (ex: 0x0483)."))

        try:
            date_str = date.today().strftime('%d/%m/%Y')
            commands = printer_service.build_test_ticket(self.academy_name, date_str)
            printer_service.print_escpos(commands, vendor_id=v_id, product_id=p_id)
        except Exception as e:
            raise UserError(_("Erreur lors de l'impression de test : %s") % str(e))
