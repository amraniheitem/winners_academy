# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError

import logging

_logger = logging.getLogger(__name__)


class WinnersAttendanceAnomaly(models.Model):
    _name = "winners.attendance.anomaly"
    _description = "Anomalie de pointage Winners"
    _order = "timestamp desc"
    _rec_name = "display_name"

    # ── Identification du pointage ──
    student_id = fields.Many2one(
        comodel_name="winners.student",
        string="Étudiant",
        index=True,
    )
    zk_device_id = fields.Integer(
        string="UID Appareil",
        help="UID tel que reçu de la pointeuse ZKTeco.",
    )
    timestamp = fields.Datetime(
        string="Horodatage du pointage",
        required=True,
        index=True,
    )

    # ── Raison de l'anomalie ──
    reason = fields.Selection(
        selection=[
            ("no_sheet", "Aucune feuille de présence trouvée"),
            ("out_of_window", "Hors fenêtre d'acceptation"),
            ("unknown_device_id", "UID inconnu (non associé à un étudiant)"),
            ("no_sessions_remaining", "Aucune séance restante dans ce groupe"),
            ("no_enrollment", "Pas d'inscription dans ce groupe"),
        ],
        string="Raison",
        required=True,
    )
    reason_detail = fields.Text(
        string="Détail",
        help="Explication technique supplémentaire.",
    )

    # ── Résolution manuelle ──
    resolved = fields.Boolean(
        string="Résolu",
        default=False,
        index=True,
    )
    resolved_by = fields.Many2one(
        comodel_name="res.users",
        string="Résolu par",
        readonly=True,
    )
    resolved_at = fields.Datetime(
        string="Résolu le",
        readonly=True,
    )
    sheet_id = fields.Many2one(
        comodel_name="winners.attendance.sheet",
        string="Feuille rattachée",
        help="Feuille de présence à laquelle le pointage a été rattaché manuellement.",
    )
    notes = fields.Text(
        string="Notes",
    )

    # ── Branche (pour les record rules) ──
    branch_id = fields.Many2one(
        comodel_name="winners.branch",
        string="Branche",
        related="student_id.branch_id",
        store=True,
        readonly=True,
    )

    # ── Display name ──
    display_name = fields.Char(
        compute="_compute_display_name",
        store=True,
    )

    @api.depends("student_id.name", "timestamp", "reason")
    def _compute_display_name(self):
        reason_labels = dict(self._fields['reason'].selection)
        for rec in self:
            student_name = rec.student_id.name or f"UID {rec.zk_device_id}"
            ts = rec.timestamp.strftime('%d/%m %H:%M') if rec.timestamp else '?'
            reason_str = reason_labels.get(rec.reason, rec.reason or '')
            rec.display_name = f"{student_name} — {ts} ({reason_str})"

    # ══════════════════════════════════════
    # ACTIONS
    # ══════════════════════════════════════

    def action_resolve(self):
        """Marquer l'anomalie comme résolue."""
        for rec in self:
            if rec.resolved:
                raise UserError("Cette anomalie est déjà marquée comme résolue.")
            rec.write({
                'resolved': True,
                'resolved_by': self.env.uid,
                'resolved_at': fields.Datetime.now(),
            })

    def action_unresolve(self):
        """Réouvrir une anomalie (Super Admin uniquement)."""
        for rec in self:
            if not self.env.user.has_group('winners_auth.winners_group_super_admin'):
                raise UserError(
                    "Seul le Super Administrateur peut réouvrir une anomalie."
                )
            rec.write({
                'resolved': False,
                'resolved_by': False,
                'resolved_at': False,
            })

    def action_link_to_sheet(self):
        """
        Rattacher manuellement le pointage à une feuille de présence.
        Marque l'étudiant présent sur la feuille sélectionnée.
        """
        self.ensure_one()
        if not self.sheet_id:
            raise UserError(
                "Veuillez d'abord sélectionner une feuille de présence "
                "dans le champ 'Feuille rattachée'."
            )
        if not self.student_id:
            raise UserError(
                "Impossible de rattacher : aucun étudiant associé à cette anomalie."
            )

        # Trouver ou créer la ligne de l'étudiant dans la feuille
        AttLine = self.env['winners.attendance.line']
        line = AttLine.search([
            ('sheet_id', '=', self.sheet_id.id),
            ('student_id', '=', self.student_id.id),
        ], limit=1)

        if not line:
            line = AttLine.create({
                'sheet_id': self.sheet_id.id,
                'student_id': self.student_id.id,
                'status': 'absent',
            })

        line.mark_present(source='zkteco')

        self.write({
            'resolved': True,
            'resolved_by': self.env.uid,
            'resolved_at': fields.Datetime.now(),
            'notes': (self.notes or '') + (
                f"\nRattaché manuellement à {self.sheet_id.display_name}"
            ),
        })

        _logger.info(
            "Anomalie %s résolue : rattachée à la feuille %s",
            self.id, self.sheet_id.display_name,
        )
