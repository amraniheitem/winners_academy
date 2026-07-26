# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError

import logging
import requests

_logger = logging.getLogger(__name__)


class WinnersStudentZkWizard(models.TransientModel):
    _name = "winners.student.zk.wizard"
    _description = "Wizard d'association empreinte ZKTeco"

    student_id = fields.Many2one(
        comodel_name="winners.student",
        string="Étudiant",
        required=True,
        readonly=True,
    )
    device_user_ids = fields.One2many(
        comodel_name="winners.student.zk.wizard.line",
        inverse_name="wizard_id",
        string="Utilisateurs sur l'appareil",
    )
    selected_line_id = fields.Many2one(
        comodel_name="winners.student.zk.wizard.line",
        string="Utilisateur sélectionné",
    )
    error_message = fields.Text(
        string="Erreur",
        readonly=True,
    )

    # ══════════════════════════════════════
    # CHARGEMENT AUTOMATIQUE À L'OUVERTURE
    # ══════════════════════════════════════

    @api.model
    def default_get(self, fields_list):
        """Charge automatiquement les utilisateurs de l'appareil à l'ouverture."""
        res = super().default_get(fields_list)
        if 'device_user_ids' in fields_list:
            student_id = res.get('student_id') or self.env.context.get('default_student_id')
            if student_id:
                try:
                    lines = self._fetch_device_users(student_id)
                    res['device_user_ids'] = [(0, 0, line) for line in lines]
                    res['error_message'] = False
                except Exception as e:
                    res['error_message'] = str(e)
                    res['device_user_ids'] = []
        return res

    # ══════════════════════════════════════
    # COMMUNICATION AVEC LE BRIDGE
    # ══════════════════════════════════════

    def _get_bridge_url(self):
        """Récupère l'URL du service ZK Bridge depuis les paramètres système."""
        ICP = self.env['ir.config_parameter'].sudo()
        url = ICP.get_param('zk_bridge_url', default='http://localhost:5000')
        return url.rstrip('/')

    def _fetch_device_users(self, student_id=None):
        """
        Appelle GET /device/users sur le service Flask.
        Retourne une liste de dicts pour créer les lignes du wizard.
        Exclut les UIDs déjà associés à d'autres étudiants.
        """
        bridge_url = self._get_bridge_url()
        try:
            response = requests.get(
                f"{bridge_url}/device/users",
                timeout=10,
            )
        except requests.ConnectionError:
            raise UserError(
                "Impossible de contacter la pointeuse.\n"
                "Vérifiez que le service ZK Bridge est démarré "
                f"({bridge_url}) et que la pointeuse est connectée."
            )
        except requests.Timeout:
            raise UserError(
                "Le service ZK Bridge ne répond pas (timeout).\n"
                "Vérifiez la connexion réseau."
            )

        if response.status_code != 200:
            data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
            error_msg = data.get('error', f'Erreur HTTP {response.status_code}')
            raise UserError(
                f"Erreur de la pointeuse : {error_msg}"
            )

        data = response.json()
        if not data.get('success'):
            raise UserError(
                f"Erreur de la pointeuse : {data.get('error', 'Erreur inconnue')}"
            )

        device_users = data.get('data', {}).get('users', [])

        # Chercher les UIDs déjà associés dans Odoo (y compris étudiants archivés)
        Student = self.env['winners.student'].sudo().with_context(active_test=False)
        linked_students = Student.search([
            ('zk_device_id', '!=', False),
            ('zk_device_id', '!=', 0),
        ])
        linked_map = {s.zk_device_id: s for s in linked_students}

        is_super_admin = self.env.user.has_group(
            'winners_auth.winners_group_super_admin'
        )

        lines = []
        for du in device_users:
            uid = du.get('uid', 0)
            linked_student = linked_map.get(uid)

            # Si l'étudiant lié est archivé ou suspendu, libérer automatiquement l'UID
            if linked_student:
                is_archived = not getattr(linked_student, 'active', True)
                is_suspended = (linked_student.status == 'suspended')
                if is_archived or is_suspended:
                    _logger.info(
                        "Wizard ZK: auto-libération de l'UID %s de l'étudiant non actif %s (id=%s)",
                        uid, linked_student.name, linked_student.id,
                    )
                    linked_student.write({
                        'zk_device_id': False,
                        'zk_device_name_snapshot': False,
                        'fingerprint_linked_date': False,
                    })
                    linked_student = None

            already_linked = bool(linked_student)
            is_self = (
                already_linked
                and student_id
                and linked_student.id == student_id
            )

            # Exclure les UIDs déjà liés à un AUTRE étudiant actif
            # sauf pour le Super Admin qui peut forcer
            if already_linked and not is_self and not is_super_admin:
                continue

            lines.append({
                'device_uid': uid,
                'device_name': du.get('name', ''),
                'device_user_id': du.get('user_id', ''),
                'already_linked': already_linked and not is_self,
                'linked_student_name': (
                    f"{linked_student.name} {linked_student.first_name or ''}"
                    if already_linked and not is_self
                    else ''
                ),
            })

        return lines

    # ══════════════════════════════════════
    # ACTIONS
    # ══════════════════════════════════════

    def action_refresh(self):
        """Rafraîchit la liste des utilisateurs depuis la pointeuse."""
        self.ensure_one()
        # Supprimer les lignes existantes
        self.device_user_ids.unlink()
        try:
            lines = self._fetch_device_users(self.student_id.id)
            for line_vals in lines:
                line_vals['wizard_id'] = self.id
                self.env['winners.student.zk.wizard.line'].create(line_vals)
            self.error_message = False
        except UserError as e:
            self.error_message = str(e)

        return {
            'type': 'ir.actions.act_window',
            'name': 'Associer une empreinte',
            'res_model': 'winners.student.zk.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_confirm(self):
        """Confirme l'association de l'empreinte sélectionnée."""
        self.ensure_one()

        if not self.selected_line_id:
            raise UserError(
                "Veuillez sélectionner un utilisateur dans la liste "
                "avant de confirmer."
            )

        line = self.selected_line_id
        student = self.student_id

        # Vérification supplémentaire anti-doublon
        if line.already_linked:
            is_super_admin = self.env.user.has_group(
                'winners_auth.winners_group_super_admin'
            )
            if not is_super_admin:
                raise UserError(
                    f"Cet UID ({line.device_uid}) est déjà associé à "
                    f"{line.linked_student_name}. "
                    "Seul le Super Administrateur peut forcer un remplacement."
                )
            # Super Admin force le remplacement : dissocier l'ancien étudiant (actif ou archivé)
            old_student = self.env['winners.student'].sudo().with_context(active_test=False).search([
                ('zk_device_id', '=', line.device_uid),
            ], limit=1)
            if old_student:
                old_student.write({
                    'zk_device_id': False,
                    'zk_device_name_snapshot': False,
                    'fingerprint_linked_date': False,
                })
                _logger.warning(
                    "Super Admin a forcé le remplacement de l'UID %s "
                    "de l'étudiant %s vers %s",
                    line.device_uid, old_student.name, student.name,
                )

        # Enregistrer l'association
        student.write({
            'zk_device_id': line.device_uid,
            'zk_device_name_snapshot': line.device_name,
            'fingerprint_linked_date': fields.Datetime.now(),
        })

        _logger.info(
            "Empreinte associée : étudiant %s ← uid %s (nom appareil: %s)",
            student.name, line.device_uid, line.device_name,
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Empreinte associée',
                'message': (
                    f"L'empreinte de {line.device_name} (UID {line.device_uid}) "
                    f"a été associée à {student.name} {student.first_name or ''}."
                ),
                'type': 'success',
                'sticky': False,
                'next': {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                }
            },
        }
