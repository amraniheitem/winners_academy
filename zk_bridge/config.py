# -*- coding: utf-8 -*-
"""
Configuration du service ZK Bridge.
Paramètres de connexion à la pointeuse ZKTeco K60 Pro.
Modifiable via variables d'environnement ou directement ici.
"""
import os

# ── Connexion ZKTeco ──
ZK_IP = os.environ.get('ZK_IP', '192.168.1.150')
ZK_PORT = int(os.environ.get('ZK_PORT', '4370'))
ZK_TIMEOUT = int(os.environ.get('ZK_TIMEOUT', '5'))
ZK_PASSWORD = int(os.environ.get('ZK_PASSWORD', '0'))

# ── Service Flask ──
FLASK_HOST = os.environ.get('FLASK_HOST', '0.0.0.0')
FLASK_PORT = int(os.environ.get('FLASK_PORT', '5000'))
FLASK_DEBUG = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
