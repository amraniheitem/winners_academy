from . import models
from odoo import api, SUPERUSER_ID, fields
import logging

_logger = logging.getLogger(__name__)

def post_init_hook(env):
    """Migration: each existing M2M link between group and student -> enrollment record."""
    Group = env['winners.group']
    Enrollment = env['winners.student.enrollment']
    
    _logger.info("Starting winners.student.enrollment migration...")
    groups = Group.search([])
    created_count = 0
    for group in groups:
        # Since group.student_ids is still M2M at this step, we can read it directly.
        for student in group.student_ids:
            # Check if enrollment already exists to avoid duplicates
            existing = Enrollment.search([
                ('student_id', '=', student.id),
                ('group_id', '=', group.id),
            ], limit=1)
            if not existing:
                Enrollment.create({
                    'student_id': student.id,
                    'group_id': group.id,
                    'sessions_remaining': student.sessions_remaining,
                    'enrollment_date': student.enrollment_date or fields.Date.today(),
                })
                created_count += 1
                
    _logger.info("Migration completed: %d enrollment(s) created.", created_count)

