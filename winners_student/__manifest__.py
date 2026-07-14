{
    "name": "Winners Student",
    "version": "17.0.2.0.0",
    "category": "Winners Academy",
    "depends": ["base", "winners_auth", "winners_branch"],
    "external_dependencies": {
        "python": ["requests"],
    },
    "data": [
        "security/ir.model.access.csv",
        "security/ir_rules.xml",
        "views/winners_student_views.xml",
        "views/winners_student_zk_wizard_views.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
}
