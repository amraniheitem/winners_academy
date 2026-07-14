# -*- coding: utf-8 -*-
"""
Processeur central de pointage ZKTeco pour Winners Academy.

Contient la logique de process_checkin et le cron de synchronisation.
"""
# pyrefly: ignore [missing-import]
from odoo import api, fields, models
# pyrefly: ignore [missing-import]
from odoo.exceptions import UserError

import logging
import requests
import traceback
import pytz
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class WinnersAttendanceProcessor(models.AbstractModel):
    _name = "winners.attendance.processor"
    _description = "Processeur de pointage ZKTeco"

    # ══════════════════════════════════════════════════════════
    # PARAMÈTRES CONFIGURABLES
    # ══════════════════════════════════════════════════════════

    def _get_checkin_window_minutes(self):
        """Récupère la fenêtre d'acceptation en minutes (défaut: 15)."""
        ICP = self.env['ir.config_parameter'].sudo()
        return int(ICP.get_param('checkin_window_minutes', '15'))

    def _get_duplicate_block_hours(self):
        """Récupère le délai anti-doublon en heures (défaut: 2)."""
        ICP = self.env['ir.config_parameter'].sudo()
        return float(ICP.get_param('checkin_duplicate_block_hours', '2'))

    def _get_bridge_url(self):
        """Récupère l'URL du service ZK Bridge (défaut: http://localhost:5000)."""
        ICP = self.env['ir.config_parameter'].sudo()
        url = ICP.get_param('zk_bridge_url', 'http://localhost:5000')
        return url.rstrip('/')

    # ══════════════════════════════════════════════════════════
    # DÉDUPLICATION PAR (user_id, timestamp)
    # ══════════════════════════════════════════════════════════

    def _is_txn_already_processed(self, zk_user_id, timestamp):
        """
        Vérifie si une transaction (zk_user_id, timestamp) a déjà été traitée.
        Retourne True si la transaction existe déjà dans la table de déduplication.
        """
        ProcessedTxn = self.env['winners.attendance.processed.txn'].sudo()
        return bool(ProcessedTxn.search([
            ('zk_user_id', '=', zk_user_id),
            ('timestamp', '=', timestamp),
        ], limit=1))

    def _mark_txn_processed(self, zk_user_id, timestamp, result):
        """
        Enregistre une transaction comme traitée dans la table de déduplication.
        """
        ProcessedTxn = self.env['winners.attendance.processed.txn'].sudo()
        try:
            ProcessedTxn.create({
                'zk_user_id': zk_user_id,
                'timestamp': timestamp,
                'result': result,
            })
        except Exception:
            # Contrainte unique violée → transaction déjà enregistrée
            # (cas de concurrence entre 2 crons simultanés, très rare)
            _logger.debug(
                "Transaction déjà enregistrée dans la table de dédup: "
                "user_id=%s, timestamp=%s",
                zk_user_id, timestamp,
            )

    # ══════════════════════════════════════════════════════════
    # MÉTHODE CENTRALE : process_checkin
    # ══════════════════════════════════════════════════════════

    @api.model
    def process_checkin(self, zk_device_id, timestamp):
        """
        Traite un pointage ZKTeco individuel.

        Ordre exact :
        1. Résoudre zk_device_id → winners.student
        2. Vérifier anti-doublon (Règle B)
        3. Chercher feuille(s) éligibles (Règle A)
        4. Marquer présent ou créer anomalie

        Args:
            zk_device_id (int): UID de l'utilisateur sur la pointeuse.
            timestamp (datetime): Horodatage du pointage.

        Returns:
            str: Résultat du traitement ('accepted', 'duplicate_ignored',
                 'anomaly_created', 'unknown_id').
        """
        Student = self.env['winners.student'].sudo()
        SyncLog = self.env['winners.attendance.sync.log'].sudo()
        Anomaly = self.env['winners.attendance.anomaly'].sudo()
        Sheet = self.env['winners.attendance.sheet'].sudo()
        AttLine = self.env['winners.attendance.line'].sudo()

        # Convertir zk_device_id en int
        try:
            zk_device_id = int(zk_device_id)
        except (ValueError, TypeError):
            _logger.warning(
                "process_checkin: zk_device_id invalide: %s", zk_device_id
            )
            return 'unknown_id'

        # Convertir timestamp en datetime si nécessaire
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                _logger.error(
                    "process_checkin: format timestamp invalide: %s", timestamp
                )
                return 'unknown_id'

        # Conserver local_timestamp et générer utc_timestamp pour les écritures Odoo
        local_timestamp = timestamp
        tz_name = self.env.user.tz or self.env.context.get('tz') or 'Africa/Algiers'
        try:
            local_tz = pytz.timezone(tz_name)
            local_dt = local_tz.localize(local_timestamp)
            utc_timestamp = local_dt.astimezone(pytz.utc).replace(tzinfo=None)
        except Exception:
            utc_timestamp = local_timestamp - timedelta(hours=1)

        _logger.info(
            "Traitement pointage reçu : UID=%s, timestamp=%s (UTC: %s)",
            zk_device_id, local_timestamp, utc_timestamp,
        )

        # ────────────────────────────────────────
        # ÉTAPE 1 : Résoudre zk_device_id → student
        # ────────────────────────────────────────
        student = Student.search([
            ('zk_device_id', '=', zk_device_id),
        ], limit=1)

        if not student:
            _logger.warning(
                "Aucun étudiant trouvé pour UID=%s",
                zk_device_id,
            )
            # Créer une anomalie
            Anomaly.create({
                'zk_device_id': zk_device_id,
                'timestamp': utc_timestamp,
                'reason': 'unknown_device_id',
                'reason_detail': (
                    f"L'UID {zk_device_id} n'est associé à aucun étudiant "
                    "dans Odoo. Vérifiez l'association dans la fiche étudiant."
                ),
            })
            # Log technique
            SyncLog.create({
                'zk_device_id': zk_device_id,
                'timestamp': utc_timestamp,
                'action': 'unknown_id',
                'details': f"UID {zk_device_id} non trouvé dans Odoo.",
            })
            return 'unknown_id'

        _logger.info(
            "Étudiant trouvé: %s %s",
            student.first_name or '', student.name,
        )

        # ────────────────────────────────────────
        # ÉTAPE 2 : Anti-doublon (Règle B)
        # ────────────────────────────────────────
        block_hours = self._get_duplicate_block_hours()

        if student.last_valid_checkin_time:
            last_checkin = fields.Datetime.from_string(
                student.last_valid_checkin_time
            )
            delta = utc_timestamp - last_checkin
            block_delta = timedelta(hours=block_hours)

            if delta < block_delta and delta.total_seconds() >= 0:
                _logger.info(
                    "Ignoré, doublon dans les 2h (dernier pointage: %s, delta: %s, seuil: %sh) pour %s",
                    last_checkin, delta, block_hours, student.name,
                )
                # Log technique UNIQUEMENT (pas d'anomalie visible)
                SyncLog.create({
                    'zk_device_id': zk_device_id,
                    'student_id': student.id,
                    'timestamp': utc_timestamp,
                    'action': 'duplicate_ignored',
                    'details': (
                        f"Pointage ignoré : {delta} depuis le dernier "
                        f"pointage valide (seuil: {block_hours}h). "
                        f"Dernier pointage: {last_checkin}"
                    ),
                })
                return 'duplicate_ignored'
            else:
                _logger.info("Pas de doublon, on continue pour %s", student.name)
        else:
            _logger.info("Pas de doublon, on continue pour %s", student.name)

        # ────────────────────────────────────────
        # ÉTAPE 3 : Chercher feuille(s) éligibles (Règle A)
        # ────────────────────────────────────────
        window_minutes = self._get_checkin_window_minutes()
        checkin_date = timestamp.date()

        # Convertir le timestamp en heure float pour comparaison
        checkin_float = timestamp.hour + timestamp.minute / 60.0

        # Fenêtre en heures float
        window_float = window_minutes / 60.0

        # Toutes les feuilles du jour non clôturées
        today_sheets = Sheet.search([
            ('date', '=', checkin_date),
            ('state', '!=', 'closed'),
        ])

        # Filtrer : le groupe contient cet étudiant
        # ET l'heure de début est dans la fenêtre
        eligible_sheets = Sheet.browse()
        for sheet in today_sheets:
            # L'étudiant doit être dans le groupe de la feuille
            if student.id not in sheet.group_id.student_ids.ids:
                continue

            # Vérifier la fenêtre de temps
            time_start = sheet.time_start
            if abs(checkin_float - time_start) <= window_float:
                eligible_sheets |= sheet

        # ────────────────────────────────────────
        # ÉTAPE 4 : Marquer présent ou créer anomalie
        # ────────────────────────────────────────
        if eligible_sheets:
            _logger.info(
                "Feuille trouvée: %s",
                ", ".join(s.display_name for s in eligible_sheets),
            )
            marked_sheets = []
            for sheet in eligible_sheets:
                # Trouver la ligne de l'étudiant dans cette feuille
                line = AttLine.search([
                    ('sheet_id', '=', sheet.id),
                    ('student_id', '=', student.id),
                ], limit=1)

                if not line:
                    # L'étudiant est dans le groupe mais pas encore
                    # de ligne dans la feuille (cas rare)
                    line = AttLine.create({
                        'sheet_id': sheet.id,
                        'student_id': student.id,
                        'status': 'absent',
                    })

                # Marquer présent via la méthode centralisée
                if line.status not in ('present', 'late'):
                    line.mark_present(source='zkteco')
                    marked_sheets.append(sheet.display_name)

            # Mettre à jour le last_valid_checkin_time
            student.write({
                'last_valid_checkin_time': utc_timestamp,
            })

            # Log technique
            SyncLog.create({
                'zk_device_id': zk_device_id,
                'student_id': student.id,
                'timestamp': utc_timestamp,
                'action': 'accepted',
                'details': (
                    f"Marqué présent sur {len(marked_sheets)} feuille(s): "
                    f"{', '.join(marked_sheets) if marked_sheets else '(déjà marqué)'}"
                ),
            })

            _logger.info(
                "Présence marquée pour %s sur %d feuille(s)",
                student.name, len(marked_sheets),
            )
            return 'accepted'

        else:
            _logger.info(
                "Aucune feuille ouverte dans la fenêtre ±%smin pour %s, création anomalie",
                window_minutes, student.name,
            )
            # Aucune feuille éligible → anomalie
            # Déterminer la raison précise
            student_sheets_today = Sheet.search([
                ('date', '=', checkin_date),
                ('group_id.student_ids', 'in', [student.id]),
            ])

            if student_sheets_today:
                reason = 'out_of_window'
                reason_detail = (
                    f"Pointage à {checkin_float:.2f}h, "
                    f"mais aucune feuille dans la fenêtre de ±{window_minutes}min. "
                    f"Feuilles du jour : "
                    + ", ".join(
                        f"{s.display_name} (début: {s.time_start:.2f}h)"
                        for s in student_sheets_today
                    )
                )
            else:
                reason = 'no_sheet'
                reason_detail = (
                    f"Aucune feuille de présence trouvée pour {student.name} "
                    f"le {checkin_date}. L'étudiant n'a peut-être pas de "
                    "créneau prévu ce jour."
                )

            Anomaly.create({
                'student_id': student.id,
                'zk_device_id': zk_device_id,
                'timestamp': utc_timestamp,
                'reason': reason,
                'reason_detail': reason_detail,
            })

            SyncLog.create({
                'zk_device_id': zk_device_id,
                'student_id': student.id,
                'timestamp': utc_timestamp,
                'action': 'anomaly_created',
                'details': reason_detail,
            })

            _logger.info(
                "Anomalie créée: %s pour %s",
                reason, student.name,
            )
            return 'anomaly_created'

    # ══════════════════════════════════════════════════════════
    # CRON & ACTION : Synchronisation pointeuse ZKTeco
    # ══════════════════════════════════════════════════════════

    @api.model
    def sync_now_and_get_results(self):
        """
        Interroge le bridge, traite les pointages, et retourne la liste
        des noms des étudiants nouvellement marqués présents.

        Déduplication par couple (user_id, timestamp) via la table
        winners.attendance.processed.txn, au lieu d'un watermark fragile.
        """
        bridge_url = self._get_bridge_url()

        _logger.info(
            "Sync ZKTeco: démarrage (bridge=%s)",
            bridge_url,
        )

        new_checkins = []

        # Appeler le bridge
        try:
            response = requests.post(
                f"{bridge_url}/device/sync_attendance",
                timeout=15,
            )
        except requests.ConnectionError:
            _logger.error(
                "Sync ZKTeco: impossible de contacter le bridge (%s). "
                "Vérifiez que le service est démarré.",
                bridge_url,
            )
            return new_checkins
        except requests.Timeout:
            _logger.error(
                "Sync ZKTeco: timeout du bridge (%s).", bridge_url,
            )
            return new_checkins

        if response.status_code != 200:
            _logger.error(
                "Sync ZKTeco: erreur HTTP %s du bridge.",
                response.status_code,
            )
            return new_checkins

        data = response.json()
        if not data.get('success'):
            _logger.error(
                "Sync ZKTeco: erreur bridge: %s",
                data.get('error', 'Erreur inconnue'),
            )
            return new_checkins

        transactions = data.get('data', {}).get('transactions', [])

        # ── Diagnostic : afficher les bornes des transactions reçues ──
        if transactions:
            timestamps_str = [t.get('timestamp', '') for t in transactions]
            _logger.info(
                "Sync ZKTeco: %d transaction(s) reçue(s) — "
                "plus ancienne: %s, plus récente: %s",
                len(transactions),
                min(timestamps_str) if timestamps_str else 'N/A',
                max(timestamps_str) if timestamps_str else 'N/A',
            )
        else:
            _logger.info("Sync ZKTeco: 0 transaction(s) reçue(s).")

        # ── Traiter chaque transaction avec déduplication (user_id, timestamp) ──
        processed = 0
        skipped_dedup = 0
        skipped_invalid = 0

        for txn in transactions:
            user_id = txn.get('user_id')
            timestamp_str = txn.get('timestamp')

            if not user_id or not timestamp_str:
                skipped_invalid += 1
                continue

            try:
                txn_timestamp = datetime.strptime(
                    timestamp_str, '%Y-%m-%d %H:%M:%S'
                )
            except ValueError:
                _logger.warning(
                    "Sync ZKTeco: timestamp invalide: %s",
                    timestamp_str,
                )
                skipped_invalid += 1
                continue

            try:
                zk_uid = int(user_id)
            except (ValueError, TypeError):
                _logger.warning(
                    "Sync ZKTeco: user_id invalide: %s", user_id,
                )
                skipped_invalid += 1
                continue

            # ── Déduplication par (user_id, timestamp) ──
            if self._is_txn_already_processed(zk_uid, txn_timestamp):
                skipped_dedup += 1
                continue

            # ── Traiter le pointage ──
            try:
                result = self.process_checkin(zk_uid, txn_timestamp)
            except Exception as e:
                _logger.error(
                    "Sync ZKTeco: ERREUR lors du traitement de "
                    "user_id=%s, timestamp=%s: %s\n%s",
                    zk_uid, txn_timestamp, str(e), traceback.format_exc(),
                )
                result = 'error'

            # ── Enregistrer comme traitée (même si erreur, pour ne pas boucler) ──
            self._mark_txn_processed(zk_uid, txn_timestamp, result)
            processed += 1

            if result == 'accepted':
                # Récupérer le nom de l'étudiant
                student = self.env['winners.student'].sudo().search([
                    ('zk_device_id', '=', zk_uid),
                ], limit=1)
                if student:
                    full_name = f"{student.first_name or ''} {student.name}"
                    new_checkins.append(full_name.strip())

        _logger.info(
            "Sync ZKTeco: terminé — %d traité(s), %d ignoré(s) (déjà traité), "
            "%d invalide(s), %d nouveau(x) présent(s).",
            processed, skipped_dedup, skipped_invalid, len(new_checkins),
        )
        return new_checkins

    @api.model
    def _cron_sync_zkteco(self):
        """Cron exécutant la synchronisation automatique."""
        now_str = fields.Datetime.now()
        _logger.info("Cron sync démarré à %s", now_str)
        try:
            new_checkins = self.sync_now_and_get_results()
            _logger.info(
                "Cron sync terminé, %d transactions traitées à %s",
                len(new_checkins), fields.Datetime.now()
            )
        except Exception as e:
            _logger.error(
                "Erreur fatale dans le cron de synchronisation ZKTeco: %s\n%s",
                str(e), traceback.format_exc()
            )
            raise

    # ══════════════════════════════════════════════════════════
    # OUTILS SUPER ADMIN : Diagnostic & Reset
    # ══════════════════════════════════════════════════════════

    @api.model
    def action_reset_watermark(self):
        """
        Réinitialise le watermark de synchronisation (Super Admin).
        Cela force le re-traitement de toutes les transactions
        qui ne sont pas déjà dans la table de déduplication.
        """
        if not self.env.user.has_group('winners_auth.winners_group_super_admin'):
            raise UserError(
                "Seul le Super Administrateur peut réinitialiser le watermark."
            )
        ICP = self.env['ir.config_parameter'].sudo()
        old_val = ICP.get_param('zk_last_sync_watermark', '')
        ICP.set_param('zk_last_sync_watermark', '')
        _logger.warning(
            "SUPER ADMIN: Watermark réinitialisé (ancienne valeur: %s)",
            old_val,
        )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Watermark réinitialisé',
                'message': (
                    f"L'ancien watermark ({old_val or 'vide'}) a été supprimé. "
                    "Les transactions seront désormais filtrées uniquement par "
                    "la table de déduplication (user_id, timestamp)."
                ),
                'type': 'warning',
                'sticky': True,
            },
        }

    @api.model
    def action_purge_processed_txn(self):
        """
        Vide la table de déduplication (Super Admin).
        Attention : cela causera le re-traitement de TOUTES les
        transactions lors de la prochaine synchronisation.
        """
        if not self.env.user.has_group('winners_auth.winners_group_super_admin'):
            raise UserError(
                "Seul le Super Administrateur peut purger la table de déduplication."
            )
        ProcessedTxn = self.env['winners.attendance.processed.txn'].sudo()
        count = ProcessedTxn.search_count([])
        ProcessedTxn.search([]).unlink()
        _logger.warning(
            "SUPER ADMIN: Table de déduplication purgée (%d entrées supprimées)",
            count,
        )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Table de déduplication purgée',
                'message': (
                    f"{count} entrée(s) supprimée(s). "
                    "La prochaine synchronisation re-traitera toutes les "
                    "transactions depuis la pointeuse."
                ),
                'type': 'warning',
                'sticky': True,
            },
        }
