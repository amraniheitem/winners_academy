from odoo import api, fields, models
from odoo.exceptions import UserError

import logging

_logger = logging.getLogger(__name__)


class WinnersStudent(models.Model):
    _name = "winners.student"
    _description = "Élève Winners"
    _rec_name = "name"

    _sql_constraints = [
        (
            'unique_zk_device_id',
            'UNIQUE(zk_device_id)',
            'Cet UID ZKTeco est déjà associé à un autre étudiant !',
        ),
    ]

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
    # COMPUTED
    # ══════════════════════════════════════

    @api.depends('zk_device_id')
    def _compute_fingerprint_linked(self):
        for student in self:
            student.fingerprint_linked = bool(student.zk_device_id)

    @api.constrains('zk_device_id')
    def _check_unique_zk_device_id(self):
        """Empêche les doublons de zk_device_id (y compris la valeur 0)."""
        for student in self:
            if not student.zk_device_id:
                continue
            duplicate = self.sudo().search([
                ('zk_device_id', '=', student.zk_device_id),
                ('id', '!=', student.id),
            ], limit=1)
            if duplicate:
                raise UserError(
                    f"L'UID ZKTeco {student.zk_device_id} est déjà associé "
                    f"à l'étudiant « {duplicate.name} » (id={duplicate.id}). "
                    "Dissociez-le d'abord avant de l'attribuer."
                )

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
