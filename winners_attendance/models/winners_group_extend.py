# -*- coding: utf-8 -*-
from odoo import models

# La logique de synchronisation lors de l'ajout d'un élève à un groupe
# est désormais gérée directement par les hooks de création sur le modèle
# winners.student.enrollment dans le module winners_enrollment.
class WinnersGroup(models.Model):
    _inherit = "winners.group"
