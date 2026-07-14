# -*- coding: utf-8 -*-
from odoo import fields, models

import logging

_logger = logging.getLogger(__name__)


class WinnersAttendanceSyncLog(models.Model):
    _name = "winners.attendance.sync.log"
    _description = "Log technique de synchronisation ZKTeco"
    _order = "timestamp desc"
    _rec_name = "display_name"

    zk_device_id = fields.Integer(
        string="UID Appareil",
        index=True,
    )
    student_id = fields.Many2one(
        comodel_name="winners.student",
        string="Étudiant",
        index=True,
    )
    timestamp = fields.Datetime(
        string="Horodatage du pointage",
        required=True,
        index=True,
    )
    action = fields.Selection(
        selection=[
            ("accepted", "Accepté (marqué présent)"),
            ("duplicate_ignored", "Doublon ignoré"),
            ("anomaly_created", "Anomalie créée"),
            ("unknown_id", "UID inconnu"),
        ],
        string="Action",
        required=True,
    )
    details = fields.Text(
        string="Détails",
    )

    # ── Display name ──
    display_name = fields.Char(
        compute="_compute_display_name",
        store=True,
    )

    def _compute_display_name(self):
        action_labels = dict(self._fields['action'].selection)
        for rec in self:
            student_name = rec.student_id.name or f"UID {rec.zk_device_id}"
            action_str = action_labels.get(rec.action, rec.action or '')
            ts = rec.timestamp.strftime('%d/%m %H:%M') if rec.timestamp else '?'
            rec.display_name = f"[{action_str}] {student_name} — {ts}"
