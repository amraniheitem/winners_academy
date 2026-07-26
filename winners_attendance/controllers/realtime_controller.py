# -*- coding: utf-8 -*-
"""
Controller Webhook pour le pointage en temps réel.
Reçoit les notifications HTTP POST envoyées immédiatement par zk_bridge.
"""
import json
import logging
from datetime import datetime

# pyrefly: ignore [missing-import]
from odoo import http, fields
# pyrefly: ignore [missing-import]
from odoo.http import request

_logger = logging.getLogger(__name__)


class WinnersRealtimeAttendanceController(http.Controller):
    """Controller Webhook Odoo pour les pointages instantanés ZKTeco."""

    @http.route(
        '/winners/realtime_checkin',
        type='http',
        auth='none',
        csrf=False,
        methods=['POST'],
    )
    def realtime_checkin(self, **kwargs):
        """
        Endpoint HTTP POST appelé par zk_bridge dès qu'un doigt est scanné.

        Payload JSON attendu :
        {
            "zk_device_id": "12",
            "timestamp": "2026-07-26 09:30:00"
        }
        """
        try:
            raw_body = request.httprequest.data.decode('utf-8') or '{}'
            data = json.loads(raw_body)
        except Exception:
            data = {}

        zk_device_id = data.get('zk_device_id') or kwargs.get('zk_device_id')
        timestamp_str = data.get('timestamp') or kwargs.get('timestamp')

        if not zk_device_id or not timestamp_str:
            _logger.warning(
                "Webhook Realtime: Données manquantes (zk_device_id=%s, timestamp=%s)",
                zk_device_id,
                timestamp_str,
            )
            return request.make_response(
                json.dumps({
                    'success': False,
                    'error': 'zk_device_id and timestamp required',
                }),
                headers=[('Content-Type', 'application/json; charset=utf-8')],
                status=400,
            )

        try:
            zk_uid = int(zk_device_id)
            txn_timestamp = datetime.strptime(
                timestamp_str, '%Y-%m-%d %H:%M:%S'
            )
        except (ValueError, TypeError) as parse_err:
            _logger.error(
                "Webhook Realtime: Données invalides (uid=%s, time=%s): %s",
                zk_device_id,
                timestamp_str,
                str(parse_err),
            )
            return request.make_response(
                json.dumps({
                    'success': False,
                    'error': f'Invalid data format: {parse_err}',
                }),
                headers=[('Content-Type', 'application/json; charset=utf-8')],
                status=400,
            )

        Processor = request.env['winners.attendance.processor'].sudo()

        # ── 1. Vérification anti-doublon ──
        if Processor._is_txn_already_processed(zk_uid, txn_timestamp):
            _logger.info(
                "Webhook Realtime: Transaction déjà traitée (UID=%s, Time=%s)",
                zk_uid,
                txn_timestamp,
            )
            return request.make_response(
                json.dumps({
                    'success': True,
                    'result': 'duplicate_ignored',
                    'message': 'Transaction déjà traitée précédemment',
                }),
                headers=[('Content-Type', 'application/json; charset=utf-8')],
            )

        # ── 2. Traitement immédiat du pointage ──
        result = Processor.process_checkin(zk_uid, txn_timestamp)

        # ── 3. Marquer comme traitée ──
        Processor._mark_txn_processed(zk_uid, txn_timestamp, result)

        _logger.info(
            "⚡ Webhook Realtime SUCCÈS: Pointage enregistré pour UID=%s -> Résultat=%s",
            zk_uid,
            result,
        )

        return request.make_response(
            json.dumps({
                'success': True,
                'result': result,
                'zk_device_id': zk_uid,
                'timestamp': timestamp_str,
            }),
            headers=[('Content-Type', 'application/json; charset=utf-8')],
        )
