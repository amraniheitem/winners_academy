# -*- coding: utf-8 -*-
"""
ZK Bridge Service — Service Flask intermédiaire entre Odoo et ZKTeco K60 Pro.

Expose une API HTTP simple pour dialoguer avec la pointeuse via pyzk.
Intègre un moteur Temps Réel (Realtime Watcher) qui pousse instantanément
chaque nouveau pointage détecté vers Odoo (Winners TV).

Usage:
    python zk_bridge_service.py

Endpoints:
    GET  /device/status          → Statut de l'appareil
    GET  /device/users           → Liste des utilisateurs enregistrés
    POST /device/sync_attendance → Lecture immédiate des transactions
"""

import logging
import os
import threading
import time
import traceback
from datetime import datetime

import requests
from flask import Flask, jsonify
from waitress import serve
from zk import ZK

from config import (
    ZK_IP,
    ZK_PORT,
    ZK_TIMEOUT,
    ZK_PASSWORD,
    FLASK_HOST,
    FLASK_PORT,
    FLASK_DEBUG,
    ODOO_URL,
    REALTIME_SYNC_ENABLED,
    REALTIME_POLL_INTERVAL,
)

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

# Lock pour empêcher la concurrence de socket entre les requêtes API et le thread temps réel
zk_lock = threading.Lock()
seen_transactions = set()
is_watcher_running = False


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
# MOTEUR TEMPS RÉEL (REALTIME WATCHER)
# ══════════════════════════════════════════════════════════

def _push_punch_to_odoo(user_id, timestamp_str):
    """Envoie un pointage individuel vers Odoo en Webhook HTTP POST."""
    url = f"{ODOO_URL}/winners/realtime_checkin"
    payload = {
        'zk_device_id': str(user_id),
        'timestamp': timestamp_str,
    }
    try:
        logger.info("⚡ TEMPS RÉEL: Envoi pointage à Odoo (UID=%s, Time=%s)", user_id, timestamp_str)
        res = requests.post(url, json=payload, timeout=4)
        if res.status_code == 200:
            logger.info("⚡ TEMPS RÉEL OK: Odoo a accepté le pointage (UID=%s)", user_id)
        else:
            logger.warning("⚡ TEMPS RÉEL WARNING: HTTP %s de Odoo - %s", res.status_code, res.text)
    except Exception as req_err:
        logger.warning("⚡ TEMPS RÉEL ERREUR: Impossible de joindre Odoo sur %s (%s)", url, str(req_err))


def _poll_and_push_new_checkins():
    """Scrute la pointeuse et pousse tout nouveau pointage immédiatement vers Odoo."""
    global seen_transactions
    if not zk_lock.acquire(blocking=False):
        # Lock déjà pris par une requête HTTP en cours, on saute ce tour
        return

    conn = None
    try:
        conn = _connect_zk()
        attendances = conn.get_attendance() or []

        # Si c'est la toute première fois qu'on lit la pointeuse au démarrage
        first_run = len(seen_transactions) == 0

        for att in attendances:
            user_id = str(att.user_id)
            timestamp = att.timestamp
            timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S') if isinstance(timestamp, datetime) else str(timestamp)
            txn_key = (user_id, timestamp_str)

            if txn_key not in seen_transactions:
                seen_transactions.add(txn_key)
                if len(seen_transactions) > 5000:
                    seen_transactions = set(list(seen_transactions)[-2000:])

                # Si ce n'est pas l'initialisation du démarrage, pousser vers Odoo
                if not first_run:
                    _push_punch_to_odoo(user_id, timestamp_str)
                else:
                    logger.debug("Initialisation: Transaction ignorée car présente au boot (%s, %s)", user_id, timestamp_str)
    except Exception as e:
        logger.debug("Realtime poll debug: %s", str(e))
    finally:
        _safe_disconnect(conn)
        zk_lock.release()


def realtime_worker():
    """Thread qui s'exécute en boucle pour la scrutation temps réel."""
    logger.info("⚡ Realtime Watcher Thread démarré (intervalle: %ss, target: %s)", REALTIME_POLL_INTERVAL, ODOO_URL)
    while True:
        try:
            if REALTIME_SYNC_ENABLED:
                _poll_and_push_new_checkins()
        except Exception as e:
            logger.error("Erreur critique dans realtime_worker: %s", str(e))
        time.sleep(REALTIME_POLL_INTERVAL)


def start_realtime_thread():
    """Démarre le thread d'arrière-plan s'il n'est pas déjà lancé."""
    global is_watcher_running
    if not is_watcher_running and REALTIME_SYNC_ENABLED:
        t = threading.Thread(target=realtime_worker, daemon=True, name="ZKRealtimeWatcher")
        t.start()
        is_watcher_running = True
        logger.info("Realtime Watcher Thread initialisé avec succès.")


# ══════════════════════════════════════════════════════════
# ENDPOINTS HTTP
# ══════════════════════════════════════════════════════════

@app.route('/device/status', methods=['GET'])
def device_status():
    """
    GET /device/status
    Retourne le statut de la pointeuse.
    """
    logger.debug("GET /device/status : Requête reçue")
    conn = None
    with zk_lock:
        try:
            conn = _connect_zk()

            firmware = conn.get_firmware_version() or 'N/A'
            serial = conn.get_serialnumber() or 'N/A'

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
                'realtime_enabled': REALTIME_SYNC_ENABLED,
            }
            logger.debug("GET /device/status : Réponse pyzk récupérée : %s", response_data)
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
    """
    logger.debug("GET /device/users : Requête reçue")
    conn = None
    with zk_lock:
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
    with zk_lock:
        try:
            conn = _connect_zk()
            attendances = conn.get_attendance()

            if attendances is None:
                attendances = []

            records = []
            for att in attendances:
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
        'version': '1.1.0 (Realtime Enabled)',
        'device_ip': ZK_IP,
        'device_port': ZK_PORT,
        'realtime_enabled': REALTIME_SYNC_ENABLED,
        'odoo_target': ODOO_URL,
    })


# ══════════════════════════════════════════════════════════
# POINT D'ENTRÉE
# ══════════════════════════════════════════════════════════

if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("ZK Bridge Service démarré (avec Moteur Temps Réel)")
    logger.info("Pointeuse: %s:%s", ZK_IP, ZK_PORT)
    logger.info("Écoute sur: %s:%s", FLASK_HOST, FLASK_PORT)
    logger.info("Cible Odoo Temps Réel: %s", ODOO_URL)
    logger.info("Serveur: Waitress (production)")
    logger.info("=" * 60)

    # Lancer le thread temps réel
    start_realtime_thread()

    serve(
        app,
        host=FLASK_HOST,
        port=FLASK_PORT,
    )
