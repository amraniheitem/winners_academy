# pyrefly: ignore [missing-import]
from datetime import timedelta
import logging

from odoo import api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class WinnersSession(models.Model):
    _name = "winners.session"
    _description = "Seance Winners"

    group_id = fields.Many2one(
        comodel_name="winners.group",
        string="Groupe",
        required=True,
    )
    branch_id = fields.Many2one(
        comodel_name="winners.branch",
        string="Branche",
        related="group_id.branch_id",
        readonly=True,
        store=True,
    )
    room_id = fields.Many2one(
        comodel_name="winners.room",
        string="Salle",
        required=True,
    )
    date = fields.Datetime(
        string="Date et heure",
        required=True,
    )
    duration_hours = fields.Float(
        string="Duree (heures)",
        default=1.5,
    )
    status = fields.Selection(
        selection=[
            ("planned", "Planifiee"),
            ("done", "Terminee"),
            ("cancelled", "Annulee"),
        ],
        string="Statut",
        default="planned",
    )
    notes = fields.Text(
        string="Notes",
    )

    @api.constrains("room_id", "date", "duration_hours", "status")
    def _check_room_availability(self):
        for rec in self:
            if not rec.room_id or not rec.date or rec.status == "cancelled":
                continue

            session_time = fields.Datetime.context_timestamp(rec, rec.date)
            start_float = session_time.hour + session_time.minute / 60.0
            end_float = start_float + (rec.duration_hours or 1.5)
            session_date = session_time.date()

            is_avail, msg = self.env['winners.room']._check_room_availability(
                rec.room_id,
                session_date,
                start_float,
                end_float,
                exclude_id=rec.id,
                exclude_model='winners.session',
                exclude_group_id=rec.group_id.id if rec.group_id else None,
            )
            if not is_avail:
                raise ValidationError(msg)

    @api.model
    def create(self, vals):
        record = super().create(vals)
        record._sync_attendance_sheet()
        return record

    def write(self, vals):
        result = super().write(vals)
        if {"group_id", "room_id", "date", "duration_hours", "status"} & set(vals):
            self._sync_attendance_sheet()
        return result

    def unlink(self):
        """Supprime proprement la feuille de présence associée lors de la suppression d'une séance."""
        if "winners.attendance.sheet" in self.env.registry:
            Sheet = self.env["winners.attendance.sheet"]
            for session in self:
                if not session.date or not session.group_id:
                    continue
                session_time = fields.Datetime.context_timestamp(session, session.date)
                session_date = session_time.date()
                start_float = session_time.hour + session_time.minute / 60.0
                sheets = Sheet.search([
                    ('date', '=', session_date),
                    ('group_id', '=', session.group_id.id),
                    ('time_start', '=', start_float),
                    ('state', '!=', 'closed'),
                ])
                if sheets:
                    sheets.unlink()
        return super().unlink()

    def _sync_attendance_sheet(self):
        if "winners.attendance.sheet" not in self.env.registry:
            return
        Sheet = self.env["winners.attendance.sheet"]
        for session in self.filtered(lambda rec: rec.status != "cancelled"):
            try:
                Sheet._create_or_update_sheet_for_session(session)
            except Exception:
                _logger.exception(
                    "Erreur lors de la synchronisation de la feuille de presence pour la seance %s.",
                    session.id,
                )
