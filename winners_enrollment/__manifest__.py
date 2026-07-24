{
    'sequence': 10,
    "name": "Winners Enrollment",
    "version": "17.0.1.0.0",
    "category": "Winners Academy",
    "summary": "Inscription étudiant-groupe avec compteur de séances par matière",
    "depends": [
        "base",
        "winners_auth",
        "winners_branch",
        "winners_student",
        "winners_group",
        "winners_schedule",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/ir_rules.xml",
        "views/winners_enrollment_views.xml",
    ],
    "installable": True,
    "auto_install": False,
    "post_init_hook": "post_init_hook",
    "license": "LGPL-3",
}

