# pyrefly: ignore [missing-import]
from odoo import api, fields, models


class WinnersRoomAvailabilityWizard(models.TransientModel):
    _name = "winners.room.availability.wizard"
    _description = "Recherche de salle vide"

    branch_id = fields.Many2one(
        "winners.branch",
        string="Branche",
        default=lambda self: self.env.user.branch_id,
    )
    room_id = fields.Many2one(
        "winners.room",
        string="Salle a verifier",
        domain="[('branch_id', '=', branch_id), ('is_active', '=', True)]",
    )
    date = fields.Date(required=True, default=fields.Date.today)
    time_start = fields.Float(string="Heure debut", required=True)
    time_end = fields.Float(string="Heure fin", required=True)
    available_room_ids = fields.Many2many(
        "winners.room",
        compute="_compute_available_room_ids",
        string="Salles disponibles",
    )
    result_message = fields.Text(readonly=True)

    @api.depends("branch_id", "room_id", "date", "time_start", "time_end")
    def _compute_available_room_ids(self):
        for wizard in self:
            rooms = self.env["winners.room"].search([
                ("is_active", "=", True),
                ("branch_id", "=", wizard.branch_id.id),
            ])
            available = self.env["winners.room"].browse()
            if wizard.date and wizard.time_end > wizard.time_start:
                for room in rooms:
                    ok, _message = self.env["winners.room"]._check_room_availability(
                        room,
                        wizard.date,
                        wizard.time_start,
                        wizard.time_end,
                    )
                    if ok:
                        available |= room
            wizard.available_room_ids = available

    def action_check_availability(self):
        self.ensure_one()
        if self.room_id:
            ok, message = self.env["winners.room"]._check_room_availability(
                self.room_id,
                self.date,
                self.time_start,
                self.time_end,
            )
            self.result_message = message
            notif_type = "success" if ok else "warning"
        else:
            names = ", ".join(self.available_room_ids.mapped("name"))
            message = names or "Aucune salle disponible pour ce creneau."
            self.result_message = message
            notif_type = "success" if names else "warning"

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Disponibilite salle",
                "message": message,
                "type": notif_type,
                "sticky": True,
            },
        }
