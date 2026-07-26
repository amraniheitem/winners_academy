from odoo import api, fields, models
from odoo.exceptions import UserError

import logging

_logger = logging.getLogger(__name__)


class WinnersStudent(models.Model):
    _name = "winners.student"
    _description = "Élève Winners"
    _rec_name = "name"


    name = fields.Char(
        string="Nom de famille",
        required=True,
    )
    first_name = fields.Char(
        string="Prénom",
    )
    birth_date = fields.Date(
        string="Date de naissance",
    )
    level = fields.Selection(
        selection=[
            ("primaire_1", "Primaire 1"),
            ("primaire_2", "Primaire 2"),
            ("primaire_3", "Primaire 3"),
            ("primaire_4", "Primaire 4"),
            ("primaire_5", "Primaire 5"),
            ("cem_1", "CEM 1"),
            ("cem_2", "CEM 2"),
            ("cem_3", "CEM 3"),
            ("cem_4", "CEM 4"),
            ("lycee_1", "Lycée 1"),
            ("lycee_2", "Lycée 2"),
            ("lycee_3", "Lycée 3"),
        ],
        string="Niveau scolaire",
    )
    photo = fields.Image(
        string="Photo",
    )
    parent_name = fields.Char(
        string="Nom du parent",
    )
    parent_phone = fields.Char(
        string="Téléphone parent",
    )
    parent_address = fields.Text(
        string="Adresse parent",
    )
    active = fields.Boolean(
        string="Actif",
        default=True,
    )
    status = fields.Selection(
        selection=[
            ("active", "Actif"),
            ("alert", "Alerte"),
            ("expired", "Expiré"),
            ("suspended", "Suspendu"),
        ],
        default="active",
    )
    sessions_remaining = fields.Integer(
        string="Séances restantes",
        default=0,
    )
    enrollment_date = fields.Date(
        string="Date d'inscription",
        default=fields.Date.today,
    )
    branch_id = fields.Many2one(
        comodel_name="winners.branch",
        string="Branche",
        default=lambda self: self.env.user.branch_id,
    )

    # ══════════════════════════════════════
    # CHAMPS BIOMÉTRIQUES (ZKTeco K60 Pro)
    # ══════════════════════════════════════

    zk_device_id = fields.Integer(
        string="UID Appareil ZKTeco",
        help="UID de l'utilisateur sur la pointeuse ZKTeco K60 Pro.",
        copy=False,
    )
    zk_device_name_snapshot = fields.Char(
        string="Nom sur l'appareil",
        help="Nom tel qu'il apparaissait sur la pointeuse au moment de l'association.",
        copy=False,
        readonly=True,
    )
    fingerprint_linked = fields.Boolean(
        string="Empreinte associée",
        compute="_compute_fingerprint_linked",
        store=True,
    )
    fingerprint_linked_date = fields.Datetime(
        string="Date d'association",
        copy=False,
        readonly=True,
    )
    last_valid_checkin_time = fields.Datetime(
        string="Dernier pointage valide",
        help="Horodatage du dernier pointage accepté (anti-doublon).",
        copy=False,
        readonly=True,
    )

    # ══════════════════════════════════════
    # COMPUTED & CONSTRAINTS
    # ══════════════════════════════════════

    @api.depends('zk_device_id')
    def _compute_fingerprint_linked(self):
        for student in self:
            student.fingerprint_linked = bool(student.zk_device_id)

    @api.constrains('zk_device_id', 'active')
    def _check_unique_zk_device_id(self):
        """
        Empêche les doublons de zk_device_id parmi les étudiants ACTIFS.
        Recherche avec active_test=False pour identifier d'éventuels conflits.
        """
        for student in self:
            if not student.zk_device_id:
                continue
            # Chercher dans TOUS les étudiants (actifs + archivés)
            duplicate = self.sudo().with_context(active_test=False).search([
                ('zk_device_id', '=', student.zk_device_id),
                ('id', '!=', student.id),
                ('active', '=', True),  # Conflit seulement si l'autre est actif
            ], limit=1)
            if duplicate:
                raise UserError(
                    f"L'UID ZKTeco {student.zk_device_id} est déjà associé "
                    f"à l'étudiant actif « {duplicate.name} {duplicate.first_name or ''} » (id={duplicate.id}). "
                    "Dissociez-le d'abord avant de l'attribuer."
                )

    # ══════════════════════════════════════
    # SURCHARGE WRITE & UNLINK (LIBÉRATION AUTO UID)
    # ══════════════════════════════════════

    def write(self, vals):
        """
        À l'archivage (active=False) ou la suspension (status='suspended'),
        libère automatiquement l'UID ZKTeco pour éviter les conflits fantômes.
        """
        releasing_archived = 'active' in vals and not vals['active']
        releasing_suspended = vals.get('status') == 'suspended'

        if releasing_archived or releasing_suspended:
            for student in self:
                if student.zk_device_id:
                    _logger.info(
                        "Auto-release UID: libération de l'UID %s de l'étudiant %s (id=%s) suite à %s",
                        student.zk_device_id, student.name, student.id,
                        'archivage' if releasing_archived else 'suspension',
                    )
            # Ajouter la réinitialisation des champs biométriques aux vals
            vals.update({
                'zk_device_id': False,
                'zk_device_name_snapshot': False,
                'fingerprint_linked_date': False,
            })

        return super().write(vals)

    def unlink(self):
        """
        À la suppression de l'étudiant, libère l'UID ZKTeco avant suppression.
        """
        for student in self:
            if student.zk_device_id:
                _logger.info(
                    "Auto-release UID: libération de l'UID %s de l'étudiant %s (id=%s) avant suppression",
                    student.zk_device_id, student.name, student.id,
                )
        return super().unlink()


    # ══════════════════════════════════════
    # ACTIONS BIOMÉTRIQUES
    # ══════════════════════════════════════

    def action_open_fingerprint_wizard(self):
        """Ouvre le wizard d'association d'empreinte ZKTeco."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Associer une empreinte',
            'res_model': 'winners.student.zk.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_student_id': self.id,
            },
        }

    def action_unlink_fingerprint(self):
        """Dissocie l'empreinte (retire le lien côté Odoo uniquement)."""
        self.ensure_one()
        if not self.zk_device_id:
            raise UserError("Aucune empreinte n'est associée à cet étudiant.")
        old_uid = self.zk_device_id
        old_name = self.zk_device_name_snapshot
        self.write({
            'zk_device_id': False,
            'zk_device_name_snapshot': False,
            'fingerprint_linked_date': False,
        })
        _logger.info(
            "Empreinte dissociée pour l'étudiant %s (ancien uid=%s, nom=%s)",
            self.name, old_uid, old_name,
        )
