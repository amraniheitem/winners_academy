{
    "name": "Winners Payment",
    "version": "17.0.1.0.0",
    "category": "Winners Academy",
    "summary": "Gestion des paiements Winners Academy",
    "depends": [
        "base",
        "winners_auth",
        "winners_branch",
        "winners_student",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/ir_rules.xml",
        "views/winners_payment_views.xml",
    ],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}