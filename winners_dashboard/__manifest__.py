{
    "name": "Winners Dashboard",
    "version": "17.0.1.0.0",
    "category": "Winners Academy",
    "summary": "Tableau de bord Winners Academy",
    "depends": [
        "winners_student",
        "winners_payment",
        "winners_attendance",
        "winners_group",
    ],
    "data": [
        "views/winners_dashboard_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "winners_dashboard/static/src/js/dashboard.js",
            "winners_dashboard/static/src/xml/dashboard_template.xml",
            "winners_dashboard/static/src/css/dashboard.css",
        ],
    },
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
