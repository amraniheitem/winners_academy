# -*- coding: utf-8 -*-
"""
Table de déduplication des transactions ZKTeco.

Stocke chaque couple (zk_user_id, timestamp) déjà traité.
Contrainte unique SQL pour garantir qu'une transaction n'est jamais
traitée deux fois, même si le bridge retourne l'historique complet
à chaque appel.
"""
# pyrefly: ignore [missing-import]
from odoo import fields, models

import logging

_logger = logging.getLogger(__name__)


class WinnersAttendanceProcessedTxn(models.Model):
    _name = "winners.attendance.processed.txn"
    _description = "Transactions ZKTeco déjà traitées (déduplication)"
    _order = "timestamp desc"

    _sql_constraints = [
        (
            'unique_txn',
            'UNIQUE(zk_user_id, timestamp)',
            'Cette transaction a déjà été traitée.',
        ),
    ]

    zk_user_id = fields.Integer(
        string="User ID pointeuse",
        required=True,
        index=True,
        help="user_id tel que reçu de la pointeuse ZKTeco.",
    )
    timestamp = fields.Datetime(
        string="Horodatage du pointage",
        required=True,
        index=True,
    )
    result = fields.Char(
        string="Résultat du traitement",
        help="Résultat retourné par process_checkin (accepted, anomaly_created, etc.).",
    )
    processed_at = fields.Datetime(
        string="Traité le",
        default=fields.Datetime.now,
    )
