from flask_login import current_user

# Scope note: this covers the app's persistent chrome (nav, common buttons, page
# headers) rather than every string in the app — full-content translation of
# book data, flash messages, etc. is out of scope.
TRANSLATIONS = {
    'en': {
        'nav.dashboard': 'Dashboard',
        'nav.catalog': 'Catalog',
        'nav.my_collection': 'My Collection',
        'nav.my_fines': 'My Fines',
        'nav.settings': 'Settings',
        'nav.logout': 'Logout',
        'nav.checkout': 'Checkout',
        'nav.fines': 'Fines',
        'nav.books': 'Books',
        'nav.students': 'Students',
        'nav.reports': 'Reports',
        'nav.analytics': 'Analytics',
        'nav.users': 'Users',
        'nav.audit_log': 'Audit Log',
        'common.search': 'Search',
        'common.filter': 'Filter',
        'common.save': 'Save',
        'common.cancel': 'Cancel',
        'common.edit': 'Edit',
        'common.approve': 'Approve',
        'common.reject': 'Reject',
        'common.view': 'View',
        'page.welcome': 'Welcome',
        'page.settings': 'Settings',
        'page.book_catalog': 'Book Catalog',
        'page.student_lookup': 'Student Lookup',
        'page.user_management': 'User Management',
    },
    'fr': {
        'nav.dashboard': 'Tableau de bord',
        'nav.catalog': 'Catalogue',
        'nav.my_collection': 'Ma collection',
        'nav.my_fines': 'Mes amendes',
        'nav.settings': 'Paramètres',
        'nav.logout': 'Déconnexion',
        'nav.checkout': 'Emprunter',
        'nav.fines': 'Amendes',
        'nav.books': 'Livres',
        'nav.students': 'Étudiants',
        'nav.reports': 'Rapports',
        'nav.analytics': 'Analytique',
        'nav.users': 'Utilisateurs',
        'nav.audit_log': "Journal d'audit",
        'common.search': 'Rechercher',
        'common.filter': 'Filtrer',
        'common.save': 'Enregistrer',
        'common.cancel': 'Annuler',
        'common.edit': 'Modifier',
        'common.approve': 'Approuver',
        'common.reject': 'Rejeter',
        'common.view': 'Voir',
        'page.welcome': 'Bienvenue',
        'page.settings': 'Paramètres',
        'page.book_catalog': 'Catalogue de livres',
        'page.student_lookup': 'Recherche d’étudiants',
        'page.user_management': 'Gestion des utilisateurs',
    },
}


def current_language():
    if current_user.is_authenticated and current_user.language_preference in TRANSLATIONS:
        return current_user.language_preference
    return 'en'


def t(key):
    lang = current_language()
    return TRANSLATIONS.get(lang, TRANSLATIONS['en']).get(key, TRANSLATIONS['en'].get(key, key))
