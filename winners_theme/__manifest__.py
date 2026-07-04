{
    'name': 'Winners Theme',
    'version': '17.0.1.0.0',
    'summary': 'Thème SaaS moderne Winners Academy pour Odoo 17',
    'description': """
        Thème Winners Academy — Style SaaS
        ====================================
        - Navbar blanche avec ombre légère (style Stripe/Linear)
        - Police Cairo (arabe + latin)
        - Boutons arrondis avec transitions fluides
        - Cartes avec élévation au hover
        - Badges de statut pill avec point coloré
        - Scrollbar fine et discrète
    """,
    'author': 'Winners Academy',
    'category': 'Theme',
    'license': 'LGPL-3',
    'depends': ['web', 'winners_dashboard'],
    'data': [
        'views/web_layout_templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'winners_theme/static/src/css/winners_theme.css',
            'winners_theme/static/src/xml/navbar_templates.xml',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
}
