# pyrefly: ignore [missing-import]
from odoo import api, fields, models
# pyrefly: ignore [missing-import]
from odoo.exceptions import UserError, AccessError

import logging

_logger = logging.getLogger(__name__)


class WinnersSalary(models.Model):
    _name = "winners.salary"
    _description = "Bulletin de salaire Winners"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "period_start desc, id desc"
    _rec_name = "name"

    def _default_absence_deduction_rate(self):
        param = self.env["ir.config_parameter"].sudo().get_param("winners_salary.default_absence_deduction_rate", "1000.0")
        try:
            return float(param)
        except ValueError:
            return 1000.0

    def _default_overtime_rate(self):
        param = self.env["ir.config_parameter"].sudo().get_param("winners_salary.default_overtime_rate", "500.0")
        try:
            return float(param)
        except ValueError:
            return 500.0

    # ══════════════════════════════════════
    # IDENTIFICATION
    # ══════════════════════════════════════

    name = fields.Char(
        string="Référence",
        compute="_compute_name",
        store=True,
        tracking=True,
    )
    teacher_id = fields.Many2one(
        comodel_name="winners.teacher",
        string="Enseignant",
        required=True,
        tracking=True,
        domain=[("is_active", "=", True)],
    )
    branch_id = fields.Many2one(
        comodel_name="winners.branch",
        string="Branche",
        related="teacher_id.branch_id",
        store=True,
        readonly=True,
    )

    # ══════════════════════════════════════
    # PÉRIODE DE PAIE
    # ══════════════════════════════════════

    period_start = fields.Date(
        string="Début de période",
        required=True,
        tracking=True,
    )
    period_end = fields.Date(
        string="Fin de période",
        required=True,
        tracking=True,
    )

    # ══════════════════════════════════════
    # SALAIRE DE BASE
    # ══════════════════════════════════════

    base_salary = fields.Float(
        string="Salaire de base (DA)",
        tracking=True,
        help="Copié depuis la fiche enseignant. Modifiable par les rôles autorisés.",
    )

    # ══════════════════════════════════════
    # SÉANCES & ABSENCES (calculés)
    # ══════════════════════════════════════

    total_sessions_planned = fields.Integer(
        string="Séances prévues",
        compute="_compute_sessions",
        store=True,
        help="Nombre total de séances planifiées sur la période.",
    )
    total_sessions_done = fields.Integer(
        string="Séances effectuées",
        compute="_compute_sessions",
        store=True,
        help="Nombre de séances marquées comme 'done' sur la période.",
    )
    absences_count = fields.Integer(
        string="Absences",
        compute="_compute_sessions",
        store=True,
        tracking=True,
        help="Séances prévues non effectuées (planned - done).",
    )
    absence_deduction_rate = fields.Float(
        string="Retenue par absence (DA)",
        default=_default_absence_deduction_rate,
        tracking=True,
        help="Montant déduit par séance manquée.",
    )
    absence_deduction = fields.Float(
        string="Retenue absences (DA)",
        compute="_compute_absence_deduction",
        store=True,
        tracking=True,
    )

    # ══════════════════════════════════════
    # HEURES SUPPLÉMENTAIRES
    # ══════════════════════════════════════

    overtime_hours = fields.Float(
        string="Heures supplémentaires",
        default=0.0,
        tracking=True,
    )
    overtime_rate = fields.Float(
        string="Taux horaire supp. (DA/h)",
        default=_default_overtime_rate,
        tracking=True,
        help="Taux horaire pour les heures supplémentaires.",
    )
    overtime_amount = fields.Float(
        string="Montant heures supp. (DA)",
        compute="_compute_overtime_amount",
        store=True,
        tracking=True,
    )

    # ══════════════════════════════════════
    # PRIMES & RETENUES MANUELLES
    # ══════════════════════════════════════

    bonus = fields.Float(
        string="Prime (DA)",
        default=0.0,
        tracking=True,
    )
    bonus_justification = fields.Text(
        string="Justification prime",
        help="Obligatoire si prime > 0.",
    )
    other_deductions = fields.Float(
        string="Autres retenues (DA)",
        default=0.0,
        tracking=True,
    )
    deductions_justification = fields.Text(
        string="Justification retenues",
        help="Obligatoire si retenues > 0.",
    )

    # ══════════════════════════════════════
    # SALAIRE NET (calculé)
    # ══════════════════════════════════════

    net_salary = fields.Float(
        string="Salaire net (DA)",
        compute="_compute_net_salary",
        store=True,
        tracking=True,
    )

    # ══════════════════════════════════════
    # WORKFLOW
    # ══════════════════════════════════════

    state = fields.Selection(
        selection=[
            ("draft", "Brouillon"),
            ("validated", "Validé"),
            ("paid", "Payé"),
        ],
        string="État",
        default="draft",
        tracking=True,
        copy=False,
    )
    validated_by = fields.Many2one(
        comodel_name="res.users",
        string="Validé par",
        readonly=True,
        copy=False,
    )
    payment_date = fields.Date(
        string="Date de paiement",
        readonly=True,
        copy=False,
        tracking=True,
    )
    notes = fields.Text(
        string="Notes",
    )

    # ══════════════════════════════════════
    # SQL CONSTRAINTS
    # ══════════════════════════════════════

    _sql_constraints = [
        (
            "unique_teacher_period",
            "UNIQUE(teacher_id, period_start, period_end)",
            "Un bulletin existe déjà pour cet enseignant sur cette période !",
        ),
    ]

    # ══════════════════════════════════════
    # COMPUTE METHODS
    # ══════════════════════════════════════

    @api.depends("teacher_id", "period_start", "period_end")
    def _compute_name(self):
        for rec in self:
            if rec.teacher_id and rec.period_start:
                month_str = rec.period_start.strftime("%Y/%m")
                rec.name = f"SAL-{month_str} — {rec.teacher_id.name}"
            else:
                rec.name = "Nouveau bulletin"

    @api.depends("teacher_id", "period_start", "period_end")
    def _compute_sessions(self):
        """Compute planned, done, and absent sessions from winners.session."""
        Session = self.env["winners.session"]
        Group = self.env["winners.group"]

        for rec in self:
            if not rec.teacher_id or not rec.period_start or not rec.period_end:
                rec.total_sessions_planned = 0
                rec.total_sessions_done = 0
                rec.absences_count = 0
                continue

            # Find all groups taught by this teacher
            groups = Group.search([
                ("teacher_id", "=", rec.teacher_id.id),
            ])

            if not groups:
                rec.total_sessions_planned = 0
                rec.total_sessions_done = 0
                rec.absences_count = 0
                continue

            # Convert period dates to datetime for session query (UTC)
            from pytz import timezone, utc
            local_tz = timezone("Africa/Algiers")
            from datetime import datetime

            start_local = local_tz.localize(
                datetime(rec.period_start.year, rec.period_start.month, rec.period_start.day, 0, 0, 0)
            )
            end_local = local_tz.localize(
                datetime(rec.period_end.year, rec.period_end.month, rec.period_end.day, 23, 59, 59)
            )
            start_utc = start_local.astimezone(utc).replace(tzinfo=None)
            end_utc = end_local.astimezone(utc).replace(tzinfo=None)

            # All sessions for teacher's groups in the period
            all_sessions = Session.search([
                ("group_id", "in", groups.ids),
                ("date", ">=", start_utc),
                ("date", "<=", end_utc),
                ("status", "!=", "cancelled"),
            ])
            done_sessions = all_sessions.filtered(lambda s: s.status == "done")

            rec.total_sessions_planned = len(all_sessions)
            rec.total_sessions_done = len(done_sessions)
            rec.absences_count = max(0, rec.total_sessions_planned - rec.total_sessions_done)

    @api.depends("absences_count", "absence_deduction_rate")
    def _compute_absence_deduction(self):
        for rec in self:
            rec.absence_deduction = rec.absences_count * rec.absence_deduction_rate

    @api.depends("overtime_hours", "overtime_rate")
    def _compute_overtime_amount(self):
        for rec in self:
            rec.overtime_amount = rec.overtime_hours * rec.overtime_rate

    @api.depends(
        "base_salary",
        "absence_deduction",
        "overtime_amount",
        "bonus",
        "other_deductions",
    )
    def _compute_net_salary(self):
        for rec in self:
            rec.net_salary = (
                rec.base_salary
                - rec.absence_deduction
                + rec.overtime_amount
                + rec.bonus
                - rec.other_deductions
            )

    # ══════════════════════════════════════
    # ONCHANGE
    # ══════════════════════════════════════

    @api.onchange("teacher_id")
    def _onchange_teacher_id(self):
        """Copy base_salary from teacher's profile when selecting a teacher."""
        if self.teacher_id:
            self.base_salary = self.teacher_id.base_salary or 0.0

    # ══════════════════════════════════════
    # BUSINESS LOGIC — ACTIONS
    # ══════════════════════════════════════

    def action_recalculate(self):
        """Force recalculate sessions/absences from winners.session data."""
        for rec in self:
            if rec.state == "paid":
                raise UserError(
                    _("Impossible de recalculer un bulletin déjà payé. Veuillez d'abord le réouvrir.")
                )
        # Trigger recomputation by invalidating cache
        self.invalidate_recordset(
            fnames=["total_sessions_planned", "total_sessions_done", "absences_count"]
        )
        self._compute_sessions()
        self.message_post(body=_("🔄 Bulletin recalculé depuis les séances."))

    def action_validate(self):
        """Validate the salary slip. Only Super Admin and Director allowed."""
        for rec in self:
            if rec.state != "draft":
                raise UserError(_("Seuls les bulletins en brouillon peuvent être validés."))
            # Check justifications
            if rec.bonus > 0 and not rec.bonus_justification:
                raise UserError(
                    _("Veuillez justifier la prime avant de valider.")
                )
            if rec.other_deductions > 0 and not rec.deductions_justification:
                raise UserError(
                    _("Veuillez justifier les retenues avant de valider.")
                )
            rec.write({
                "state": "validated",
                "validated_by": self.env.uid,
            })
            rec.message_post(
                body=_("✅ Bulletin validé par %s.") % self.env.user.name
            )

    def action_pay(self):
        """Mark as paid. Only Super Admin and Director allowed."""
        for rec in self:
            if rec.state != "validated":
                raise UserError(
                    _("Seuls les bulletins validés peuvent être marqués comme payés.")
                )
            rec.write({
                "state": "paid",
                "payment_date": fields.Date.today(),
            })
            rec.message_post(
                body=_("💰 Salaire payé le %s par %s.") % (fields.Date.today(), self.env.user.name)
            )

    def action_reset_to_draft(self):
        """Reset to draft. Only Super Admin allowed (enforced via view attrs)."""
        for rec in self:
            if rec.state not in ("validated", "paid"):
                raise UserError(_("Ce bulletin est déjà en brouillon."))
            # Check if user is super admin
            is_super_admin = self.env.user.has_group(
                "winners_auth.winners_group_super_admin"
            )
            if not is_super_admin:
                raise AccessError(
                    _("Seul le Super Administrateur peut réouvrir un bulletin payé.")
                )
            rec.write({
                "state": "draft",
                "validated_by": False,
                "payment_date": False,
            })
            rec.message_post(
                body=_("🔓 Bulletin réouvert (brouillon) par %s.") % self.env.user.name
            )

    # ══════════════════════════════════════
    # WRITE PROTECTION
    # ══════════════════════════════════════

    def write(self, vals):
        """Prevent modifications on paid slips unless user is Super Admin."""
        for rec in self:
            if rec.state == "paid":
                # Allow only state changes (for reset_to_draft)
                allowed_fields = {"state", "validated_by", "payment_date", "message_follower_ids", "message_ids", "activity_ids"}
                changing_fields = set(vals.keys())
                if not changing_fields.issubset(allowed_fields):
                    is_super_admin = self.env.user.has_group(
                        "winners_auth.winners_group_super_admin"
                    )
                    if not is_super_admin:
                        raise UserError(
                            _("Ce bulletin est payé et verrouillé. Seul le Super Administrateur peut le modifier.")
                        )
        return super().write(vals)
