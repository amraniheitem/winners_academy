# pyrefly: ignore [missing-import]
from odoo import api, fields, models
# pyrefly: ignore [missing-import]
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval

import logging

_logger = logging.getLogger(__name__)

# Day-of-week mapping: Python weekday() → winners.schedule day_of_week key
WEEKDAY_MAP = {
    0: 'monday',
    1: 'tuesday',
    2: 'wednesday',
    3: 'thursday',
    4: 'friday',
    5: 'saturday',
    6: 'sunday',
}


class WinnersAttendanceSheet(models.Model):
    _name = "winners.attendance.sheet"
    _description = "Feuille de présence Winners"
    _order = "date desc, time_start asc"
    _rec_name = "display_name"

    _sql_constraints = [
        (
            'unique_schedule_date',
            'UNIQUE(schedule_id, date)',
            'Une feuille de présence existe déjà pour ce créneau et cette date !',
        ),
    ]

    @api.constrains('room_id', 'date', 'time_start', 'time_end', 'state')
    def _check_room_overlap(self):
        """Vérifie les conflits de salle mais ne bloque JAMAIS l'accès à la feuille.
        L'utilisateur doit pouvoir entrer dans la feuille pour corriger le problème."""
        for rec in self:
            if not rec.room_id or not rec.date or rec.state == 'closed':
                continue
            is_avail, msg = self.env['winners.room']._check_room_availability(
                rec.room_id,
                rec.date,
                rec.time_start,
                rec.time_end,
                exclude_id=rec.id,
                exclude_model='winners.attendance.sheet',
                exclude_schedule_id=rec.schedule_id.id if rec.schedule_id else None,
                exclude_group_id=rec.group_id.id if rec.group_id else None,
                check_schedules=False,
                check_sheets=True,
            )
            if not is_avail:
                # Log l'avertissement mais ne bloque pas — l'utilisateur doit pouvoir
                # ouvrir la feuille pour corriger la salle ou l'horaire.
                _logger.warning("Conflit de salle détecté sur feuille %s: %s", rec.id, msg)

    # ── Identité du créneau ──
    date = fields.Date(
        string="Date",
        required=True,
        default=fields.Date.today,
        index=True,
    )
    schedule_id = fields.Many2one(
        comodel_name="winners.schedule",
        string="Créneau horaire",
        ondelete="set null",
        index=True,
    )
    group_id = fields.Many2one(
        comodel_name="winners.group",
        string="Groupe",
        required=True,
        index=True,
    )
    teacher_id = fields.Many2one(
        comodel_name="winners.teacher",
        string="Enseignant",
        related="group_id.teacher_id",
        readonly=True,
        store=True,
    )
    room_id = fields.Many2one(
        comodel_name="winners.room",
        string="Salle",
        required=True,
    )
    branch_id = fields.Many2one(
        comodel_name="winners.branch",
        string="Branche",
        related="group_id.branch_id",
        readonly=True,
        store=True,
    )
    subject = fields.Selection(
        related="group_id.subject",
        string="Matière",
        readonly=True,
        store=True,
    )
    time_start = fields.Float(
        string="Heure début",
    )
    time_end = fields.Float(
        string="Heure fin",
    )

    # ── État ──
    state = fields.Selection(
        selection=[
            ("open", "Ouverte"),
            ("in_progress", "En cours"),
            ("closed", "Clôturée"),
        ],
        string="État",
        default="open",
        required=True,
        index=True,
    )

    # ── Lignes de présence ──
    line_ids = fields.One2many(
        comodel_name="winners.attendance.line",
        inverse_name="sheet_id",
        string="Lignes de présence",
    )

    # ── Compteurs ──
    present_count = fields.Integer(
        string="Présents",
        compute="_compute_counts",
        store=True,
    )
    total_count = fields.Integer(
        string="Total inscrits",
        compute="_compute_counts",
        store=True,
    )
    progress_display = fields.Char(
        string="Présents / Total",
        compute="_compute_counts",
        store=True,
    )

    # ── Clôture ──
    closed_by = fields.Many2one(
        comodel_name="res.users",
        string="Clôturé par",
        readonly=True,
    )
    closed_at = fields.Datetime(
        string="Clôturé le",
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

    @api.depends("line_ids", "line_ids.status")
    def _compute_counts(self):
        for sheet in self:
            lines = sheet.line_ids
            sheet.total_count = len(lines)
            sheet.present_count = len(lines.filtered(
                lambda l: l.status in ('present', 'late')
            ))
            sheet.progress_display = f"{sheet.present_count}/{sheet.total_count}"

    @api.depends("group_id.name", "date", "time_start")
    def _compute_display_name(self):
        for sheet in self:
            start_h = int(sheet.time_start)
            start_m = int(round((sheet.time_start - start_h) * 60))
            time_str = f"{start_h:02d}:{start_m:02d}"
            sheet.display_name = (
                f"{sheet.group_id.name or '?'} — "
                f"{sheet.date or '?'} {time_str}"
            )

    # ══════════════════════════════════════
    # ACTIONS (WORKFLOW)
    # ══════════════════════════════════════

    def action_close(self):
        """Clôturer la feuille de présence."""
        for sheet in self:
            if sheet.state == 'closed':
                raise UserError("Cette feuille est déjà clôturée.")
            sheet.write({
                'state': 'closed',
                'closed_by': self.env.uid,
                'closed_at': fields.Datetime.now(),
            })

    def action_reopen(self):
        """Réouvrir une feuille clôturée (Super Admin uniquement)."""
        user = self.env.user
        is_super_admin = user.has_group('winners_auth.winners_group_super_admin')
        for sheet in self:
            if not is_super_admin:
                raise UserError(
                    "Seul le Super Administrateur peut réouvrir "
                    "une feuille clôturée."
                )
            sheet.write({
                'state': 'open',
                'closed_by': False,
                'closed_at': False,
            })

    def action_add_student_manually(self):
        """Ouvre le wizard pour ajouter un étudiant manuellement."""
        self.ensure_one()
        return {
            'name': "Ajouter un étudiant",
            'type': 'ir.actions.act_window',
            'res_model': 'winners.attendance.add.student.wizard',
            'view_mode': 'form',
            'context': {'default_sheet_id': self.id},
            'target': 'new',
        }

    # ══════════════════════════════════════
    # GÉNÉRATION AUTOMATIQUE (CRON)
    # ══════════════════════════════════════

    @api.model
    def _generate_daily_sheets(self, target_date=None):
        """
        Génère les feuilles de présence pour une date donnée,
        basé sur les créneaux actifs de winners.schedule.

        Appelé par le cron quotidien ou manuellement par le Super Admin.
        Anti-doublon : vérifie qu'aucune feuille n'existe déjà
        pour le même schedule_id + date.
        """
        if target_date is None:
            target_date = fields.Date.today()

        if isinstance(target_date, str):
            target_date = fields.Date.from_string(target_date)

        # Déterminer le jour de la semaine
        day_key = WEEKDAY_MAP.get(target_date.weekday())
        if not day_key:
            _logger.warning(
                "Attendance generation: unknown weekday %s for date %s",
                target_date.weekday(), target_date,
            )
            return self.browse()

        _logger.info(
            "Generating attendance sheets for %s (%s)...",
            target_date, day_key,
        )

        # Récupérer tous les créneaux actifs pour ce jour
        Schedule = self.env['winners.schedule']
        schedules = Schedule.search([
            ('day_of_week', '=', day_key),
            ('is_active', '=', True),
        ])

        if not schedules:
            _logger.info(
                "No active schedules found for %s. Nothing to generate.",
                day_key,
            )
            return self.browse()

        # Récupérer les feuilles déjà existantes pour cette date
        existing = self.search([
            ('date', '=', target_date),
            ('schedule_id', 'in', schedules.ids),
        ])
        existing_schedule_ids = set(existing.mapped('schedule_id.id'))

        created_sheets = self.browse()
        for sched in schedules:
            if sched.id in existing_schedule_ids:
                _logger.debug(
                    "Sheet already exists for schedule %s on %s, skipping.",
                    sched.id, target_date,
                )
                continue

            sheet = self.create({
                'date': target_date,
                'schedule_id': sched.id,
                'group_id': sched.group_id.id,
                'room_id': sched.room_id.id,
                'time_start': sched.time_start,
                'time_end': sched.time_end,
                'state': 'open',
            })
            created_sheets |= sheet

        # Générer également des feuilles pour les séances ponctuelles du jour
        Session = self.env['winners.session']
        sessions = Session.search([
            ('date', '>=', fields.Datetime.from_string(f'{target_date} 00:00:00')),
            ('date', '<=', fields.Datetime.from_string(f'{target_date} 23:59:59')),
            ('status', '!=', 'cancelled'),
        ])

        for session in sessions:
            if not session.date:
                continue
            session_time = fields.Datetime.context_timestamp(session, session.date)
            start_float = session_time.hour + session_time.minute / 60.0

            existing_sheet = self.search([
                ('date', '=', target_date),
                ('group_id', '=', session.group_id.id),
                ('time_start', '=', start_float),
            ], limit=1)
            if existing_sheet:
                continue

            sheet = self.create({
                'date': target_date,
                'schedule_id': False,
                'group_id': session.group_id.id,
                'room_id': session.room_id.id,
                'time_start': start_float,
                'time_end': start_float + (session.duration_hours or 1.5),
                'state': 'open',
            })
            created_sheets |= sheet

        _logger.info(
            "Generated %d new attendance sheets for %s (skipped %d existing).",
            len(created_sheets),
            target_date,
            len(existing_schedule_ids),
        )

        # Remplir les lignes d'étudiants pour chaque feuille créée
        for sheet in created_sheets:
            sheet._populate_lines()

        return created_sheets

    @api.model
    def _create_or_update_sheet_for_session(self, session):
        """Cree ou met a jour la feuille liee a une seance ponctuelle."""
        if not session.date or not session.group_id:
            return self.browse()

        session_time = fields.Datetime.context_timestamp(session, session.date)
        session_date = session_time.date()
        start_float = session_time.hour + session_time.minute / 60.0
        duration = session.duration_hours or 1.5

        sheet = self.search([
            ('date', '=', session_date),
            ('group_id', '=', session.group_id.id),
            ('time_start', '=', start_float),
        ], limit=1)

        vals = {
            'date': session_date,
            'schedule_id': False,
            'group_id': session.group_id.id,
            'room_id': session.room_id.id,
            'time_start': start_float,
            'time_end': start_float + duration,
            'state': 'open',
        }

        if sheet:
            sheet.write({
                'group_id': vals['group_id'],
                'time_end': vals['time_end'],
            })
        else:
            sheet = self.create(vals)

        sheet._populate_lines()
        return sheet

    def _populate_lines(self):
        """
        Remplit automatiquement les lignes de présence avec
        tous les étudiants inscrits au groupe de cette feuille.
        Seuls les étudiants non suspendus sont ajoutés.
        """
        self.ensure_one()
        AttLine = self.env['winners.attendance.line']

        active_enrollments = self.group_id.enrollment_ids.filtered(
            lambda enrollment: enrollment.status == 'active'
            and enrollment.student_id.status != 'suspended'
        )
        students = active_enrollments.mapped('student_id') or self.group_id.student_ids.filtered(
            lambda student: student.status != 'suspended'
        )

        existing_student_ids = set(
            self.line_ids.mapped('student_id.id')
        )

        lines_to_create = []
        for student in students:
            if student.id in existing_student_ids:
                continue
            lines_to_create.append({
                'sheet_id': self.id,
                'student_id': student.id,
                'status': 'absent',
            })

        if lines_to_create:
            AttLine.create(lines_to_create)
            _logger.info(
                "Populated sheet %s with %d student lines.",
                self.display_name, len(lines_to_create),
            )

        # Vérifier rétroactivement si des transactions déjà enregistrées
        # correspondent à cette feuille (cas nouveau groupe créé après pointage)
        self._retroactive_match_transactions()

    def _retroactive_match_transactions(self):
        """
        Après création/peuplement d'une feuille, vérifie si des transactions
        déjà enregistrées dans processed.txn correspondent à cette feuille.

        Cas d'usage principal : un nouveau groupe est créé, les étudiants
        avaient déjà pointé — leurs transactions ont été traitées comme
        anomalies ou pour d'autres groupes, mais pas pour cette nouvelle feuille.

        Cette méthode est idempotente : si un étudiant est déjà marqué
        présent, il est ignoré.
        """
        self.ensure_one()

        ProcessedTxn = self.env['winners.attendance.processed.txn'].sudo()
        AttLine = self.env['winners.attendance.line'].sudo()

        # Récupérer les étudiants de cette feuille qui ont un zk_device_id
        active_enrollments = self.group_id.enrollment_ids.filtered(
            lambda enrollment: enrollment.status == 'active'
            and enrollment.student_id.zk_device_id
            and enrollment.student_id.status != 'suspended'
        )
        students_with_zk = active_enrollments.mapped('student_id') or self.group_id.student_ids.filtered(
            lambda student: student.zk_device_id and student.status != 'suspended'
        )

        if not students_with_zk:
            return

        # Map zk_device_id → student
        zk_to_student = {s.zk_device_id: s for s in students_with_zk}
        zk_ids = list(zk_to_student.keys())

        # Chercher les transactions du jour pour ces UIDs
        sheet_date = self.date
        start_dt = fields.Datetime.from_string(f'{sheet_date} 00:00:00')
        end_dt = fields.Datetime.from_string(f'{sheet_date} 23:59:59')

        transactions = ProcessedTxn.search([
            ('zk_user_id', 'in', zk_ids),
            ('timestamp', '>=', start_dt),
            ('timestamp', '<=', end_dt),
        ])

        if not transactions:
            return

        # Fenêtre de temps configurable
        ICP = self.env['ir.config_parameter'].sudo()
        window_minutes = int(ICP.get_param('checkin_window_minutes', '15'))
        window_float = window_minutes / 60.0

        matched_count = 0
        for txn in transactions:
            student = zk_to_student.get(txn.zk_user_id)
            if not student:
                continue

            local_dt = txn.timestamp

            checkin_float = local_dt.hour + local_dt.minute / 60.0

            # Vérifier si dans la fenêtre de temps de cette feuille
            in_window = (
                abs(checkin_float - self.time_start) <= window_float
                or (self.time_start <= checkin_float <= self.time_end)
            )
            if not in_window:
                continue

            # Trouver la ligne de l'étudiant dans cette feuille
            line = AttLine.search([
                ('sheet_id', '=', self.id),
                ('student_id', '=', student.id),
            ], limit=1)

            if line and line.status not in ('present', 'late'):
                line.mark_present(source='zkteco')
                matched_count += 1
                _logger.info(
                    "Retroactive match: %s marqué(e) présent(e) sur %s "
                    "(transaction %s à %s)",
                    student.name, self.display_name,
                    txn.zk_user_id, local_dt,
                )

        if matched_count:
            _logger.info(
                "Retroactive match terminé: %d étudiant(s) marqué(s) "
                "présent(s) sur la feuille %s.",
                matched_count, self.display_name,
            )

    # ══════════════════════════════════════
    # BOUTON RÉGÉNÉRATION MANUELLE
    # ══════════════════════════════════════

    @api.model
    def action_open_today_attendance(self):
        """Ouvre la vue des feuilles de présence du jour sans régénérer les feuilles supprimées."""
        action = self.env.ref('winners_attendance.action_winners_attendance_sheet_today').read()[0]
        context = action.get('context') or {}
        if isinstance(context, str):
            context = safe_eval(context) if context else {}
        action['context'] = dict(context, search_default_today=1)
        return action

    def action_regenerate_today(self):
        """
        Action accessible par le Super Admin pour
        régénérer les feuilles du jour.
        """
        user = self.env.user
        is_super_admin = user.has_group('winners_auth.winners_group_super_admin')
        if not is_super_admin:
            raise UserError(
                "Seul le Super Administrateur peut régénérer "
                "les feuilles de présence."
            )

        sheets = self._generate_daily_sheets()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Génération terminée',
                'message': f'{len(sheets)} nouvelle(s) feuille(s) créée(s).',
                'type': 'success',
                'sticky': False,
            },
        }

    def action_sync_zkteco_button(self):
        """Bouton manuel pour synchroniser la pointeuse depuis la vue liste des feuilles."""
        Processor = self.env['winners.attendance.processor']
        new_checkins = Processor.sync_now_and_get_results()
        sync_report = Processor.get_last_sync_report()
        
        if new_checkins:
            names_str = ", ".join(new_checkins)
            title = "Nouveaux pointages détectés"
            message = f"Les étudiants suivants ont été marqués présents : {names_str}"
            notif_type = "success"
        else:
            title = "Pointeuse synchronisée"
            message = "Aucun nouveau pointage détecté."
            notif_type = "info"
            title = "Diagnostic synchronisation"
            if sync_report.get('bridge_count'):
                message = (
                    "Aucun etudiant marque present. "
                    f"Bridge: {sync_report.get('bridge_count')} transaction(s), "
                    f"traitees: {sync_report.get('processed')}, "
                    f"deja traitees: {sync_report.get('skipped_dedup')}, "
                    f"invalides: {sync_report.get('skipped_invalid')}, "
                    f"retraitement: {sync_report.get('reprocess_results')}. "
                    f"Dernier pointage pointeuse: {sync_report.get('latest_timestamp') or 'N/A'}."
                )
            else:
                message = (
                    "Aucune transaction recue depuis la pointeuse. "
                    f"Bridge: {sync_report.get('bridge_url') or 'N/A'}."
                )
            notif_type = "warning"
            
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'message': message,
                'type': notif_type,
                'sticky': False,
                'next': {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                }
            }
        }

    def action_reprocess_zkteco_today_button(self):
        """Retraite les transactions du jour non acceptees."""
        Processor = self.env['winners.attendance.processor']
        report = Processor.reprocess_today_not_accepted()
        accepted_names = report.get('accepted_names', [])
        result_counts = report.get('results', {})
        details = ", ".join(
            f"{result}: {count}" for result, count in sorted(result_counts.items())
        ) or "aucune transaction a retraiter"

        if accepted_names:
            message = (
                "Presences recuperees : "
                + ", ".join(accepted_names)
                + f". Details: {details}"
            )
            notif_type = "success"
        else:
            message = f"Aucune nouvelle presence acceptee. Details: {details}"
            notif_type = "warning"

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Retraitement ZKTeco termine',
                'message': message,
                'type': notif_type,
                'sticky': True,
                'next': {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                }
            }
        }

    def action_generate_today_button(self):
        """Bouton manuel pour générer les feuilles de présence d'aujourd'hui."""
        sheets = self._generate_daily_sheets()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Génération terminée',
                'message': f"{len(sheets)} nouvelle(s) feuille(s) de présence créée(s) pour aujourd'hui.",
                'type': 'success',
                'sticky': False,
                'next': {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                }
            }
        }

    # ══════════════════════════════════════
    # CRON : Mise à jour des états
    # ══════════════════════════════════════

    @api.model
    def _cron_update_sheet_states(self):
        """
        Cron léger (toutes les 5 min) pour mettre à jour
        les états des feuilles du jour :
        - open → in_progress si l'heure actuelle est dans le créneau
        - in_progress → open si l'heure est hors créneau (et pas clôturée)
        """
        from pytz import timezone
        from datetime import datetime

        today = fields.Date.today()
        local_tz = timezone('Africa/Algiers')
        now_local = datetime.now(local_tz)
        current_float = now_local.hour + now_local.minute / 60.0

        sheets = self.search([
            ('date', '=', today),
            ('state', 'in', ['open', 'in_progress']),
        ])

        for sheet in sheets:
            if sheet.time_start <= current_float < sheet.time_end:
                if sheet.state != 'in_progress':
                    sheet.state = 'in_progress'
            else:
                if sheet.state == 'in_progress':
                    # Si on a dépassé l'heure de fin, clôturer auto
                    if current_float >= sheet.time_end:
                        sheet.write({
                            'state': 'closed',
                            'closed_at': fields.Datetime.now(),
                        })
                    else:
                        sheet.state = 'open'
