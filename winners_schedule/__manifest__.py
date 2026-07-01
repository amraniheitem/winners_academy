{
    "name": "Winners Schedule",
    "version": "17.0.1.0.0",
    "category": "Winners Academy",
    "summary": "Gestion de l'emploi du temps Winners Academy",
    "depends": [
        "base",
        "winners_auth",
        "winners_branch",
        "winners_teacher",
        "winners_group",
        "winners_room",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/winners_schedule_views.xml",
    ],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
