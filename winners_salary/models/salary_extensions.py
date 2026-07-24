# pyrefly: ignore [missing-import]
from odoo import api, fields, models
from odoo.exceptions import AccessError


class WinnersGroup(models.Model):
    _inherit = "winners.group"

    earning_cycle = fields.Selection(
        [
            ("every_4_sessions", "Chaque 4 seances"),
            ("monthly", "Mensuel"),
        ],
        string="Cycle de gains",
        default="every_4_sessions",
        required=True,
    )


class WinnersTeacher(models.Model):
    _inherit = "winners.teacher"

    commission_percentage = fields.Float(
        string="Commission enseignant (%)",
        default=50.0,
    )

    def write(self, vals):
        if "commission_percentage" in vals and not (
            self.env.user.has_group("winners_auth.winners_group_super_admin")
            or self.env.user.has_group("winners_auth.winners_group_director")
        ):
            raise AccessError("Vous n'avez pas le droit de modifier la commission.")

        old_values = {
            teacher.id: teacher.commission_percentage
            for teacher in self
        } if "commission_percentage" in vals else {}
        result = super().write(vals)

        if "commission_percentage" in vals:
            Log = self.env["winners.teacher.commission.log"].sudo()
            for teacher in self:
                old_value = old_values.get(teacher.id)
                if old_value != teacher.commission_percentage:
                    Log.create({
                        "teacher_id": teacher.id,
                        "old_percentage": old_value,
                        "new_percentage": teacher.commission_percentage,
                    })
        return result


class WinnersAttendanceSheet(models.Model):
    _inherit = "winners.attendance.sheet"

    earning_processed = fields.Boolean(default=False, copy=False, index=True)
    teacher_snapshot_id = fields.Many2one(
        "winners.teacher",
        string="Enseignant reel",
        copy=False,
        index=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("teacher_snapshot_id") and vals.get("group_id"):
                group = self.env["winners.group"].browse(vals["group_id"])
                vals["teacher_snapshot_id"] = group.teacher_id.id or False
        return super().create(vals_list)

    def action_close(self):
        result = super().action_close()
        EarningSheet = self.env["winners.teacher.earning.sheet"]
        for sheet in self:
            if not sheet.teacher_snapshot_id:
                sheet.teacher_snapshot_id = sheet.teacher_id.id or sheet.group_id.teacher_id.id
            EarningSheet.generate_for_group_if_ready(sheet.group_id)
        return result


class WinnersSalary(models.Model):
    _inherit = "winners.salary"

    teaching_commission = fields.Float(
        string="Commissions enseignement (DA)",
        compute="_compute_teaching_commission",
    )

    @api.depends("teacher_id", "period_start", "period_end")
    def _compute_teaching_commission(self):
        EarningSheet = self.env["winners.teacher.earning.sheet"]
        for salary in self:
            if not salary.teacher_id or not salary.period_start or not salary.period_end:
                salary.teaching_commission = 0.0
                continue
            sheets = EarningSheet.search([
                ("teacher_id", "=", salary.teacher_id.id),
                ("state", "=", "treated"),
                ("period_start", ">=", salary.period_start),
                ("period_end", "<=", salary.period_end),
            ])
            salary.teaching_commission = sum(sheets.mapped("teacher_amount"))

    @api.depends(
        "base_salary",
        "absence_deduction",
        "overtime_amount",
        "bonus",
        "other_deductions",
        "teaching_commission",
    )
    def _compute_net_salary(self):
        super()._compute_net_salary()
        for salary in self:
            salary.net_salary += salary.teaching_commission
