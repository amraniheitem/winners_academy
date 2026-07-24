# -*- coding: utf-8 -*-
"""
ZK Bridge Service — Service Flask intermédiaire entre Odoo et ZKTeco K60 Pro.

Expose une API HTTP simple pour dialoguer avec la pointeuse via pyzk.
Conçu pour tourner en continu sur le PC serveur (transformable en service
Windows via NSSM).

Usage:
    python zk_bridge_service.py

Endpoints:
    GET  /device/status          → Statut de l'appareil
    GET  /device/users           → Liste des utilisateurs enregistrés
    POST /device/sync_attendance → Lecture immédiate des transactions
"""

import logging
import traceback
from datetime import datetime

from flask import Flask, jsonify
from zk import ZK

from config import (
    ZK_IP,
    ZK_PORT,
    ZK_TIMEOUT,
    ZK_PASSWORD,
    FLASK_HOST,
    FLASK_PORT,
    FLASK_DEBUG,
)

import os
# ── Logging ──
log_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', '%Y-%m-%d %H:%M:%S')

# File handler (writes to zk_bridge.log)
log_file_path = os.path.join(os.path.dirname(__file__), 'zk_bridge.log')
file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
file_handler.setFormatter(log_formatter)
file_handler.setLevel(logging.DEBUG)

# Console handler (standard output)
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
console_handler.setLevel(logging.INFO)

logger = logging.getLogger('zk_bridge')
logger.setLevel(logging.DEBUG)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Supprimer le handler par défaut pour éviter le double log sur la console
logging.getLogger().handlers = []
logging.getLogger().addHandler(file_handler)
logging.getLogger().addHandler(console_handler)
logging.getLogger().setLevel(logging.INFO)

app = Flask(__name__)


# ══════════════════════════════════════════════════════════
# HELPER : connexion sécurisée à la pointeuse
# ══════════════════════════════════════════════════════════

class ZKConnectionError(Exception):
    """Exception levée quand la pointeuse est injoignable."""
    pass


def _connect_zk():
    """
    Établit une connexion à la pointeuse ZKTeco.
    Retourne l'objet connexion.
    Lève ZKConnectionError si la connexion échoue.
    """
    try:
        zk = ZK(ZK_IP, port=ZK_PORT, timeout=ZK_TIMEOUT, password=ZK_PASSWORD)
        conn = zk.connect()
        if conn is None:
            raise ZKConnectionError("Connexion retournée None")
        logger.info("Connecté à la pointeuse %s:%s", ZK_IP, ZK_PORT)
        # Synchronisation automatique de l'heure pour éviter tout décalage
        try:
            conn.set_time(datetime.now())
            logger.debug("Heure de la pointeuse synchronisée avec le serveur.")
        except Exception as te:
            logger.warning("Impossible de synchroniser l'heure de la pointeuse : %s", str(te))
        return conn
    except ZKConnectionError:
        raise
    except Exception as e:
        logger.error("Impossible de se connecter à la pointeuse: %s", str(e))
        raise ZKConnectionError(
            f"Impossible de se connecter à la pointeuse ({ZK_IP}:{ZK_PORT}): {str(e)}"
        )


def _safe_disconnect(conn):
    """Déconnecte proprement, sans lever d'exception."""
    try:
        if conn:
            conn.disconnect()
            logger.info("Déconnecté de la pointeuse.")
    except Exception as e:
        logger.warning("Erreur lors de la déconnexion: %s", str(e))


def _error_response(message, status_code=503):
    """Génère une réponse d'erreur standardisée."""
    return jsonify({
        'success': False,
        'error': message,
        'data': None,
    }), status_code


def _success_response(data):
    """Génère une réponse de succès standardisée."""
    return jsonify({
        'success': True,
        'error': None,
        'data': data,
    }), 200


# ══════════════════════════════════════════════════════════
# ENDPOINTS
# ══════════════════════════════════════════════════════════

@app.route('/device/status', methods=['GET'])
def device_status():
    """
    GET /device/status
    Retourne le statut de la pointeuse : firmware, nombre d'empreintes,
    nombre de transactions, statut de connexion.
    """
    logger.debug("GET /device/status : Requête reçue")
    conn = None
    try:
        conn = _connect_zk()

        firmware = conn.get_firmware_version() or 'N/A'
        serial = conn.get_serialnumber() or 'N/A'

        # Nombre d'empreintes et de transactions
        # Le K60 Pro supporte get_fp_version et les compteurs
        try:
            finger_count = conn.get_fp_version()
        except Exception:
            finger_count = 'N/A'

        try:
            users = conn.get_users()
            user_count = len(users) if users else 0
        except Exception:
            user_count = 'N/A'

        try:
            attendances = conn.get_attendance()
            attendance_count = len(attendances) if attendances else 0
        except Exception:
            attendance_count = 'N/A'

        response_data = {
            'connected': True,
            'ip': ZK_IP,
            'port': ZK_PORT,
            'firmware': firmware,
            'serial_number': serial,
            'user_count': user_count,
            'finger_count': finger_count,
            'transaction_count': attendance_count,
        }
        logger.debug("GET /device/status : Réponse pyzk récupérée : %s", response_data)
        logger.debug("GET /device/status : Envoi de la réponse à Odoo")
        return _success_response(response_data)

    except ZKConnectionError as e:
        return _error_response(str(e), 503)

    except Exception as e:
        logger.error("Erreur inattendue dans /device/status: %s\n%s",
                      str(e), traceback.format_exc())
        return _error_response(f"Erreur inattendue: {str(e)}", 500)

    finally:
        _safe_disconnect(conn)


@app.route('/device/users', methods=['GET'])
def device_users():
    """
    GET /device/users
    Retourne la liste brute des utilisateurs enregistrés SUR L'APPAREIL.
    Chaque utilisateur contient : uid, name, user_id.
    """
    logger.debug("GET /device/users : Requête reçue")
    conn = None
    try:
        conn = _connect_zk()
        users = conn.get_users()

        if users is None:
            users = []

        user_list = []
        for user in users:
            user_list.append({
                'uid': user.uid,
                'name': user.name or '',
                'user_id': user.user_id or '',
                'privilege': user.privilege,
            })

        logger.info("Récupéré %d utilisateur(s) depuis la pointeuse.", len(user_list))
        response_data = {
            'users': user_list,
            'count': len(user_list),
        }
        logger.debug("GET /device/users : Réponse pyzk récupérée : %s", response_data)
        logger.debug("GET /device/users : Envoi de la réponse à Odoo")
        return _success_response(response_data)

    except ZKConnectionError as e:
        return _error_response(str(e), 503)

    except Exception as e:
        logger.error("Erreur inattendue dans /device/users: %s\n%s",
                      str(e), traceback.format_exc())
        return _error_response(f"Erreur inattendue: {str(e)}", 500)

    finally:
        _safe_disconnect(conn)


@app.route('/device/sync_attendance', methods=['POST'])
def sync_attendance():
    """
    POST /device/sync_attendance
    Force une lecture immédiate des dernières transactions d'attendance
    depuis la pointeuse et les retourne.
    """
    logger.debug("POST /device/sync_attendance : Requête reçue")
    conn = None
    try:
        conn = _connect_zk()
        attendances = conn.get_attendance()

        if attendances is None:
            attendances = []

        records = []
        for att in attendances:
            # att.user_id est l'identifiant utilisateur sur la pointeuse
            # att.timestamp est un objet datetime
            # att.status est le type de pointage (check-in/check-out)
            # att.punch est le type de punch
            timestamp = att.timestamp
            if isinstance(timestamp, datetime):
                timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
            else:
                timestamp_str = str(timestamp)

            records.append({
                'user_id': str(att.user_id),
                'timestamp': timestamp_str,
                'status': att.status,
                'punch': att.punch,
                'uid': getattr(att, 'uid', None),
            })

        logger.info(
            "Synchronisation: %d transaction(s) lue(s) depuis la pointeuse.",
            len(records),
        )
        response_data = {
            'transactions': records,
            'count': len(records),
            'sync_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
        logger.debug("POST /device/sync_attendance : Réponse pyzk récupérée (%d transactions)", len(records))
        logger.debug("POST /device/sync_attendance : Envoi de la réponse à Odoo")
        return _success_response(response_data)

    except ZKConnectionError as e:
        return _error_response(str(e), 503)

    except Exception as e:
        logger.error("Erreur inattendue dans /device/sync_attendance: %s\n%s",
                      str(e), traceback.format_exc())
        return _error_response(f"Erreur inattendue: {str(e)}", 500)

    finally:
        _safe_disconnect(conn)


# ══════════════════════════════════════════════════════════
# HEALTH CHECK
# ══════════════════════════════════════════════════════════

@app.route('/', methods=['GET'])
def health():
    """Endpoint de santé pour vérifier que le service tourne."""
    return _success_response({
        'service': 'ZK Bridge',
        'version': '1.0.0',
        'device_ip': ZK_IP,
        'device_port': ZK_PORT,
    })


# ══════════════════════════════════════════════════════════
# POINT D'ENTRÉE
# ══════════════════════════════════════════════════════════

if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("ZK Bridge Service démarré")
    logger.info("Pointeuse: %s:%s", ZK_IP, ZK_PORT)
    logger.info("Écoute sur: %s:%s", FLASK_HOST, FLASK_PORT)
    logger.info("=" * 60)

    app.run(
        host=FLASK_HOST,
        port=FLASK_PORT,
        debug=FLASK_DEBUG,
    )
