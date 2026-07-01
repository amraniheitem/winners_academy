{
    "name": "Winners Group",
    "version": "17.0.1.0.0",
    "category": "Winners Academy",
    "summary": "Gestion des groupes et séances Winners Academy",
    "depends": [
        "base",
        "winners_auth",
        "winners_branch",
        "winners_student",
        "winners_teacher",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/winners_group_views.xml",
    ],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
