# pyrefly: ignore [missing-import]
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError
from datetime import timedelta


class WinnersTeacherCommissionLog(models.Model):
    _name = "winners.teacher.commission.log"
    _description = "Historique commission enseignant"
    _order = "changed_at desc"

    teacher_id = fields.Many2one("winners.teacher", required=True, ondelete="cascade")
    changed_by = fields.Many2one("res.users", default=lambda self: self.env.user, readonly=True)
    changed_at = fields.Datetime(default=fields.Datetime.now, readonly=True)
    old_percentage = fields.Float(readonly=True)
    new_percentage = fields.Float(readonly=True)


class WinnersTeacherEarningSheet(models.Model):
    _name = "winners.teacher.earning.sheet"
    _description = "Bordereau de gains enseignant"
    _order = "period_start desc, id desc"
    _rec_name = "name"

    name = fields.Char(compute="_compute_name", store=True)
    teacher_id = fields.Many2one("winners.teacher", required=True, index=True)
    group_id = fields.Many2one("winners.group", required=True, index=True)
    branch_id = fields.Many2one(
        "winners.branch",
        related="group_id.branch_id",
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.company.currency_id,
        required=True,
    )
    period_start = fields.Date(required=True, index=True)
    period_end = fields.Date(required=True, index=True)
    commission_percentage = fields.Float(required=True)
    session_price = fields.Monetary(required=True, currency_field="currency_id")
    state = fields.Selection(
        [("not_treated", "Non traité"), ("treated", "Traité")],
        default="not_treated",
        required=True,
        index=True,
    )
    treated_by = fields.Many2one("res.users", readonly=True)
    treated_at = fields.Datetime(readonly=True)
    line_ids = fields.One2many(
        "winners.teacher.earning.sheet.line",
        "earning_sheet_id",
        string="Séances",
    )
    total_present_count = fields.Integer(compute="_compute_amounts", store=True)
    total_amount = fields.Monetary(compute="_compute_amounts", store=True, currency_field="currency_id")
    teacher_amount = fields.Monetary(compute="_compute_amounts", store=True, currency_field="currency_id")
    company_amount = fields.Monetary(compute="_compute_amounts", store=True, currency_field="currency_id")

    @api.depends("teacher_id", "group_id", "period_start", "period_end")
    def _compute_name(self):
        for sheet in self:
            if sheet.teacher_id and sheet.group_id and sheet.period_start:
                sheet.name = f"GAIN-{sheet.period_start:%Y/%m} - {sheet.teacher_id.name} - {sheet.group_id.name}"
            else:
                sheet.name = _("Nouveau bordereau")

    @api.depends("line_ids.present_count", "session_price", "commission_percentage")
    def _compute_amounts(self):
        for sheet in self:
            present_count = sum(sheet.line_ids.mapped("present_count"))
            total = present_count * sheet.session_price
            teacher_amount = total * sheet.commission_percentage / 100.0
            sheet.total_present_count = present_count
            sheet.total_amount = total
            sheet.teacher_amount = teacher_amount
            sheet.company_amount = total - teacher_amount

    def action_mark_treated(self):
        if not (
            self.env.user.has_group("winners_auth.winners_group_super_admin")
            or self.env.user.has_group("winners_auth.winners_group_director")
        ):
            raise AccessError(_("Vous n'avez pas le droit de traiter ce bordereau."))
        for sheet in self:
            if sheet.state == "treated":
                raise UserError(_("Ce bordereau est déjà traité."))
            sheet.write({
                "state": "treated",
                "treated_by": self.env.uid,
                "treated_at": fields.Datetime.now(),
            })

    def action_reset_not_treated(self):
        if not self.env.user.has_group("winners_auth.winners_group_super_admin"):
            raise AccessError(_("Seul le Super Administrateur peut rouvrir un bordereau."))
        self.write({
            "state": "not_treated",
            "treated_by": False,
            "treated_at": False,
        })

    @api.model
    def _present_count_for_sheet(self, attendance_sheet):
        return len(attendance_sheet.line_ids.filtered(lambda line: line.status in ("present", "late")))

    @api.model
    def _teacher_for_attendance_sheet(self, attendance_sheet):
        return attendance_sheet.teacher_snapshot_id or attendance_sheet.teacher_id or attendance_sheet.group_id.teacher_id

    @api.model
    def _create_from_attendance_sheets(self, attendance_sheets):
        created = self.browse()
        sheets_by_key = {}
        processable_sheets = self.env["winners.attendance.sheet"].browse()
        for attendance_sheet in attendance_sheets:
            teacher = self._teacher_for_attendance_sheet(attendance_sheet)
            if not teacher:
                continue
            processable_sheets |= attendance_sheet
            sheets_by_key.setdefault((teacher.id, attendance_sheet.group_id.id), self.env["winners.attendance.sheet"].browse())
            sheets_by_key[(teacher.id, attendance_sheet.group_id.id)] |= attendance_sheet

        for (teacher_id, group_id), sheets in sheets_by_key.items():
            teacher = self.env["winners.teacher"].browse(teacher_id)
            group = self.env["winners.group"].browse(group_id)
            ordered_sheets = sheets.sorted(lambda sheet: (sheet.date, sheet.time_start, sheet.id))
            earning_sheet = self.create({
                "teacher_id": teacher.id,
                "group_id": group.id,
                "period_start": ordered_sheets[0].date,
                "period_end": ordered_sheets[-1].date,
                "commission_percentage": teacher.commission_percentage,
                "session_price": group.session_price,
            })
            line_vals = []
            for index, attendance_sheet in enumerate(ordered_sheets, start=1):
                line_vals.append({
                    "earning_sheet_id": earning_sheet.id,
                    "sequence_in_batch": index,
                    "attendance_sheet_id": attendance_sheet.id,
                    "present_count": self._present_count_for_sheet(attendance_sheet),
                })
            self.env["winners.teacher.earning.sheet.line"].create(line_vals)
            created |= earning_sheet

        if created:
            processable_sheets.write({"earning_processed": True})
        return created

    @api.model
    def generate_for_group_if_ready(self, group):
        if group.earning_cycle != "every_4_sessions":
            return self.browse()
        sheets = self.env["winners.attendance.sheet"].search([
            ("group_id", "=", group.id),
            ("state", "=", "closed"),
            ("earning_processed", "=", False),
        ], order="date asc, time_start asc, id asc")
        created = self.browse()
        while len(sheets) >= 4:
            batch = sheets[:4]
            created |= self._create_from_attendance_sheets(batch)
            sheets = sheets[4:]
        return created

    @api.model
    def cron_generate_monthly_earnings(self):
        today = fields.Date.today()
        first_this_month = today.replace(day=1)
        period_end = first_this_month - timedelta(days=1)
        period_start = period_end.replace(day=1)

        Group = self.env["winners.group"]
        created = self.browse()
        for group in Group.search([("earning_cycle", "=", "monthly")]):
            sheets = self.env["winners.attendance.sheet"].search([
                ("group_id", "=", group.id),
                ("state", "=", "closed"),
                ("earning_processed", "=", False),
                ("date", ">=", period_start),
                ("date", "<=", period_end),
            ], order="date asc, time_start asc, id asc")
            if sheets:
                created |= self._create_from_attendance_sheets(sheets)
        return created


class WinnersTeacherEarningSheetLine(models.Model):
    _name = "winners.teacher.earning.sheet.line"
    _description = "Ligne de bordereau de gains enseignant"
    _order = "sequence_in_batch, id"

    earning_sheet_id = fields.Many2one(
        "winners.teacher.earning.sheet",
        required=True,
        ondelete="cascade",
    )
    sequence_in_batch = fields.Integer(required=True)
    attendance_sheet_id = fields.Many2one("winners.attendance.sheet", required=True, ondelete="restrict")
    session_date = fields.Date(related="attendance_sheet_id.date", store=True, readonly=True)
    present_count = fields.Integer(required=True)
