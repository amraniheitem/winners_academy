# -*- coding: utf-8 -*-
from odoo import fields, models


class WinnersStudentZkWizardLine(models.TransientModel):
    _name = "winners.student.zk.wizard.line"
    _description = "Ligne wizard ZKTeco (utilisateur appareil)"

    wizard_id = fields.Many2one(
        comodel_name="winners.student.zk.wizard",
        string="Wizard",
        required=True,
        ondelete="cascade",
    )
    device_uid = fields.Integer(
        string="UID",
        readonly=True,
    )
    device_name = fields.Char(
        string="Nom sur l'appareil",
        readonly=True,
    )
    device_user_id = fields.Char(
        string="ID utilisateur",
        readonly=True,
    )
    already_linked = fields.Boolean(
        string="Déjà lié",
        readonly=True,
    )
    linked_student_name = fields.Char(
        string="Associé à",
        readonly=True,
    )

    def action_select_and_confirm(self):
        """Associe directement cet utilisateur de l'appareil à l'étudiant."""
        self.ensure_one()
        self.wizard_id.selected_line_id = self.id
        return self.wizard_id.action_confirm()

