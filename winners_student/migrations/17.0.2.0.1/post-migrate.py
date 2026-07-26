from odoo import SUPERUSER_ID


def migrate(cr, version):
    if not version:
        return

    cr.execute(
        """
        ALTER TABLE winners_student
        ADD COLUMN IF NOT EXISTS active boolean DEFAULT TRUE
        """
    )
    cr.execute(
        """
        UPDATE winners_student
        SET active = TRUE
        WHERE active IS NULL
        """
    )
