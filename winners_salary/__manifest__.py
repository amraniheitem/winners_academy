{
    'sequence': 10,
    "name": "Winners Salary",
    "version": "17.0.1.0.0",
    "category": "Winners Academy",
    "summary": "Gestion des salaires des enseignants Winners Academy",
    "description": """
Module de gestion des bulletins de salaire pour Winners Academy.
- Calcul dynamique basé sur les séances (présences / absences)
- Heures supplémentaires, primes, retenues
- Workflow : Brouillon → Validé → Payé
- Sécurité multi-niveaux par rôle et branche
- Rapport PDF bilingue FR/AR
- Audit trail complet (mail.thread)
    """,
    "depends": [
        "base",
        "mail",
        "winners_auth",
        "winners_branch",
        "winners_teacher",
        "winners_group",
        "winners_attendance",
        "winners_schedule",
    ],
    "data": [
        "security/winners_salary_security.xml",
        "security/ir.model.access.csv",
        "data/teacher_earning_cron.xml",
        "views/teacher_earning_views.xml",
        "views/winners_salary_views.xml",
        "reports/winners_salary_report.xml",
        "data/salary_config_data.xml",
    ],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}

