# pyrefly: ignore [missing-import]
from odoo import api, fields, models

import logging

_logger = logging.getLogger(__name__)


class WinnersStudentEnrollment(models.Model):
    _name = "winners.student.enrollment"
    _description = "Inscription étudiant-groupe"
    _rec_name = "display_name"
    _order = "student_id, group_id"

    _sql_constraints = [
        (
            'unique_student_group',
            'UNIQUE(student_id, group_id)',
            "Un étudiant ne peut avoir qu'une inscription par groupe !",
        ),
    ]

    # ── Relations principales ──
    student_id = fields.Many2one(
        comodel_name="winners.student",
        string="Étudiant",
        required=True,
        ondelete="cascade",
        index=True,
    )
    group_id = fields.Many2one(
        comodel_name="winners.group",
        string="Groupe",
        required=True,
        ondelete="cascade",
        index=True,
    )

    # ── Compteur de séances ──
    sessions_remaining = fields.Integer(
        string="Séances restantes",
        default=0,
        readonly=True,
    )

    # ── Statut (computed depuis sessions_remaining) ──
    status = fields.Selection(
        selection=[
            ("active", "Actif"),
            ("alert", "Alerte"),
            ("expired", "Expiré"),
            ("suspended", "Suspendu"),
        ],
        string="Statut",
        compute="_compute_status",
        store=True,
        readonly=False,
    )

    # ── Date d'inscription ──
    enrollment_date = fields.Date(
        string="Date d'inscription",
        default=fields.Date.today,
    )

    # ── Champs related pour affichage / filtrage ──
    branch_id = fields.Many2one(
        comodel_name="winners.branch",
        string="Branche",
        related="group_id.branch_id",
        store=True,
        readonly=True,
    )
    subject = fields.Selection(
        related="group_id.subject",
        string="Matière",
        store=True,
        readonly=True,
    )
    group_name = fields.Char(
        related="group_id.name",
        string="Nom du groupe",
        readonly=True,
    )

    # ── Display name ──
    display_name = fields.Char(
        compute="_compute_display_name",
        store=True,
    )

    # ══════════════════════════════════════
    # COMPUTED
    # ══════════════════════════════════════

    @api.depends('sessions_remaining')
    def _compute_status(self):
        for rec in self:
            # Ne pas écraser le statut 'suspended' qui est défini manuellement
            if rec.status == 'suspended':
                continue
            if rec.sessions_remaining > 2:
                rec.status = 'active'
            elif rec.sessions_remaining >= 1:
                rec.status = 'alert'
            else:
                rec.status = 'expired'

    @api.depends('student_id.name', 'student_id.first_name', 'group_id.name')
    def _compute_display_name(self):
        for rec in self:
            student_name = f"{rec.student_id.first_name or ''} {rec.student_id.name or ''}".strip()
            rec.display_name = f"{student_name} — {rec.group_id.name or '?'}"

    # ══════════════════════════════════════
    # ACTIONS
    # ══════════════════════════════════════

    def action_suspend(self):
        """Suspendre l'inscription."""
        for rec in self:
            rec.status = 'suspended'

    def action_reactivate(self):
        """Réactiver l'inscription (recalculer le statut depuis sessions_remaining)."""
        for rec in self:
            if rec.sessions_remaining > 2:
                rec.status = 'active'
            elif rec.sessions_remaining >= 1:
                rec.status = 'alert'
            else:
                rec.status = 'expired'

    # ══════════════════════════════════════
    # CRÉATION → ajout aux feuilles ouvertes
    # ══════════════════════════════════════

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._add_to_open_sheets()
        return records

    def _add_to_open_sheets(self):
        """
        Quand un enrollment est créé, ajouter l'étudiant aux feuilles
        de présence ouvertes du jour pour ce groupe (même logique que
        l'ancien winners_group_extend.write).
        """
        # Guard: winners.attendance.sheet may not be loaded yet during
        # initial module installation (post_init_hook runs before
        # winners_attendance is loaded).
        if 'winners.attendance.sheet' not in self.env.registry:
            return

        today = fields.Date.today()
        AttendanceSheet = self.env['winners.attendance.sheet']
        AttendanceLine = self.env['winners.attendance.line']

        for enrollment in self.filtered(lambda e: e.status != 'suspended'):
            sheets = AttendanceSheet.search([
                ('group_id', '=', enrollment.group_id.id),
                ('date', '=', today),
                ('state', 'in', ['open', 'in_progress']),
            ])

            for sheet in sheets:
                existing = set(sheet.line_ids.mapped('student_id.id'))
                if enrollment.student_id.id not in existing:
                    AttendanceLine.create({
                        'sheet_id': sheet.id,
                        'student_id': enrollment.student_id.id,
                        'status': 'absent',
                    })
                    _logger.info(
                        "Enrollment: added %s to attendance sheet %s",
                        enrollment.student_id.name,
                        sheet.display_name,
                    )
