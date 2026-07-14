# pyrefly: ignore [missing-import]
from odoo import api, fields, models
# pyrefly: ignore [missing-import]
from odoo.exceptions import UserError

import logging

_logger = logging.getLogger(__name__)


class WinnersAttendanceLine(models.Model):
    _name = "winners.attendance.line"
    _description = "Ligne de présence Winners"
    _order = "student_id"

    _sql_constraints = [
        (
            'unique_sheet_student',
            'UNIQUE(sheet_id, student_id)',
            'Cet étudiant a déjà une ligne dans cette feuille !',
        ),
    ]

    # ── Feuille parent ──
    sheet_id = fields.Many2one(
        comodel_name="winners.attendance.sheet",
        string="Feuille",
        required=True,
        ondelete="cascade",
        index=True,
    )

    # ── Étudiant ──
    student_id = fields.Many2one(
        comodel_name="winners.student",
        string="Étudiant",
        required=True,
        index=True,
    )

    # ── Statut de présence ──
    status = fields.Selection(
        selection=[
            ("absent", "Absent"),
            ("present", "Présent"),
            ("late", "En retard"),
        ],
        string="Statut",
        default="absent",
        required=True,
    )

    # ── Traçabilité du marquage ──
    marked_by = fields.Many2one(
        comodel_name="res.users",
        string="Marqué par",
        readonly=True,
    )
    marked_at = fields.Datetime(
        string="Marqué le",
        readonly=True,
    )
    source = fields.Selection(
        selection=[
            ("manual", "Manuel"),
            ("zkteco", "ZKTeco K60"),
        ],
        string="Source",
        readonly=True,
    )

    # ── Notes ──
    notes = fields.Text(
        string="Notes",
    )

    # ── Related fields for display / filtering ──
    sheet_date = fields.Date(
        related="sheet_id.date",
        string="Date",
        store=True,
        readonly=True,
    )
    sheet_state = fields.Selection(
        related="sheet_id.state",
        string="État feuille",
        store=True,
        readonly=True,
    )
    group_id = fields.Many2one(
        related="sheet_id.group_id",
        string="Groupe",
        store=True,
        readonly=True,
    )
    branch_id = fields.Many2one(
        related="sheet_id.branch_id",
        string="Branche",
        store=True,
        readonly=True,
    )

    # ══════════════════════════════════════
    # MÉTHODE CENTRALE : mark_present
    # ══════════════════════════════════════

    def mark_present(self, source='manual'):
        """
        Méthode centralisée pour marquer un étudiant comme présent.

        Conçue pour être réutilisable :
        - source='manual' : clic de la secrétaire/professeur
        - source='zkteco' : futur rattachement via pointeuse ZKTeco K60 Pro

        La même logique s'applique dans les deux cas :
        1. Vérifier que la feuille n'est pas clôturée
        2. Mettre le status à 'present'
        3. Enregistrer qui a marqué et quand
        4. Décrémenter les séances restantes de l'étudiant
        """
        for line in self:
            # Vérifier l'état de la feuille
            if line.sheet_id.state == 'closed':
                user = self.env.user
                is_super_admin = user.has_group(
                    'winners_auth.winners_group_super_admin'
                )
                if not is_super_admin:
                    raise UserError(
                        "Impossible de modifier une feuille clôturée. "
                        "Contactez le Super Administrateur."
                    )

            # Éviter le double comptage
            if line.status == 'present':
                continue

            old_status = line.status

            line.write({
                'status': 'present',
                'marked_by': self.env.uid,
                'marked_at': fields.Datetime.now(),
                'source': source,
            })

            # Décrémenter les séances uniquement si
            # passage de absent/late → present
            if old_status != 'present':
                line._deduct_session()

    def mark_late(self, source='manual'):
        """Marquer comme en retard (compte comme présent pour la déduction)."""
        for line in self:
            if line.sheet_id.state == 'closed':
                user = self.env.user
                is_super_admin = user.has_group(
                    'winners_auth.winners_group_super_admin'
                )
                if not is_super_admin:
                    raise UserError(
                        "Impossible de modifier une feuille clôturée."
                    )

            if line.status in ('present', 'late'):
                continue

            old_status = line.status

            line.write({
                'status': 'late',
                'marked_by': self.env.uid,
                'marked_at': fields.Datetime.now(),
                'source': source,
            })

            if old_status == 'absent':
                line._deduct_session()

    def mark_absent(self):
        """Remettre à absent (annulation de marquage)."""
        for line in self:
            if line.sheet_id.state == 'closed':
                user = self.env.user
                is_super_admin = user.has_group(
                    'winners_auth.winners_group_super_admin'
                )
                if not is_super_admin:
                    raise UserError(
                        "Impossible de modifier une feuille clôturée."
                    )

            if line.status == 'absent':
                continue

            old_status = line.status

            line.write({
                'status': 'absent',
                'marked_by': False,
                'marked_at': False,
                'source': False,
            })

            # Recréditer la séance si on annule un marquage
            if old_status in ('present', 'late'):
                line._credit_session()

    # ══════════════════════════════════════
    # BOUTONS D'ACTION POUR LA VUE
    # ══════════════════════════════════════

    def action_mark_present(self):
        """Bouton vue : marquer présent."""
        self.mark_present(source='manual')

    def action_mark_late(self):
        """Bouton vue : marquer en retard."""
        self.mark_late(source='manual')

    def action_mark_absent(self):
        """Bouton vue : remettre absent."""
        self.mark_absent()

    # ══════════════════════════════════════
    # GESTION DES SÉANCES RESTANTES
    # ══════════════════════════════════════

    def _deduct_session(self):
        """Décrémente les séances restantes et met à jour le statut étudiant."""
        self.ensure_one()
        student = self.student_id
        if student.sessions_remaining <= 0:
            raise UserError(
                "L'étudiant %s n'a plus de séances restantes !"
                % student.name
            )
        student.sessions_remaining -= 1
        # Mise à jour du statut de l'étudiant
        if student.sessions_remaining > 2:
            student.status = "active"
        elif student.sessions_remaining >= 1:
            student.status = "alert"
        else:
            student.status = "expired"

    def _credit_session(self):
        """Recrédite une séance (en cas d'annulation de marquage)."""
        self.ensure_one()
        student = self.student_id
        student.sessions_remaining += 1
        # Recalculer le statut
        if student.sessions_remaining > 2:
            student.status = "active"
        elif student.sessions_remaining >= 1:
            student.status = "alert"
        else:
            student.status = "expired"

    # ══════════════════════════════════════
    # PROTECTION ÉCRITURE
    # ══════════════════════════════════════

    def write(self, vals):
        """Empêche la modification si la feuille est clôturée (sauf Super Admin)."""
        if 'status' not in vals:
            # Si on ne change pas le status, vérifier quand même la clôture
            for line in self:
                if line.sheet_id.state == 'closed':
                    user = self.env.user
                    is_super_admin = user.has_group(
                        'winners_auth.winners_group_super_admin'
                    )
                    if not is_super_admin:
                        raise UserError(
                            "Impossible de modifier une ligne sur "
                            "une feuille clôturée."
                        )
        return super().write(vals)
