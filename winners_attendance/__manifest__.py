{
    "name": "Winners Attendance",
    "version": "17.0.1.0.0",
    "category": "Winners Academy",
    "summary": "Gestion des présences Winners Academy",
    "depends": [
        "base",
        "winners_auth",
        "winners_branch",
        "winners_student",
        "winners_group",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/winners_attendance_views.xml",
    ],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
