import sys
import odoo
from odoo import api, SUPERUSER_ID

config_file = r"C:\odoo17\odoo.conf"
odoo.tools.config.parse_config(["-c", config_file, "-d", "odoo-test"])

# Complete translation dictionary
TR_MAP = {
    # MENUS
    "Winners Academy": "أكاديمية وينرز",
    "Personnes": "الأشخاص",
    "Employés": "الموظفون",
    "Étudiants": "الطلاب والمسجلون",
    "Enseignants": "الأساتذة والمحاضرون",
    "Paiements": "المدفوعات",
    "Salaires": "الرواتب",
    "Bordereaux enseignant": "كشوف الأساتذة",
    "Présences": "الحضور",
    "Présences du jour": "حضور اليوم",
    "Emploi du temps": "جدول الحصص",
    "Statistiques": "الإحصائيات",
    "Paramètres": "الإعدادات",
    "Imprimante Thermique": "الطابعة الحرارية",
    "Chercher salle libre": "البحث عن قاعة",
    "Tableau de bord": "لوحة التحكم",
    "Branches": "الفروع",
    "Branche": "الفرع",
    "Pointage": "البصمة والحضور",
    "Groupes": "الأفواج",
    "Groupe": "الفوج",
    "Salles": "القاعات",
    "Salle": "القاعة",
    "Inscriptions": "التسجيلات",
    "Inscription": "التسجيل",
    "Créneaux horaires": "المواعيد الحصص",
    "Bordereau de Salaire": "كشف الراتب",
    "Imprimer Bordereau": "طباعة الكشف",
    "Imprimer Bon": "طباعة السند",
    "Bon de Paiement": "سند الدفع",

    # FIELDS & HEADERS
    "Nom": "الاسم",
    "Prénom": "اللقب",
    "Nom complet": "الاسم واللقب",
    "Matière": "المادة",
    "Téléphone": "الهاتف",
    "Téléphone tuteur": "هاتف الولي",
    "Adresse": "العنوان",
    "Statut": "الحالة",
    "État": "الحالة",
    "Actif": "نشط",
    "Inactif": "غير نشط",
    "Niveau": "المستوى",
    "Niveau d'étude": "المستوى الدراسي",
    "Niveau scolaire": "المستوى الدراسي",
    "Parent / Tuteur": "ولي الأمر",
    "Parent / Contact": "ولي الأمر",
    "Matricule": "رقم التسجيل",
    "Solde restant": "الرصيد المتبقي",
    "Séances restantes": "الحصص المتبقية",
    "Séances utilisées": "الحصص المستعملة",
    "Séances achetées": "الحصص المشتراة",
    "Séances prévues": "الحصص المبرمجة",
    "Séances effectuées": "الحصص المنجزة",
    "Absences": "الغيابات",
    "Montant": "المبلغ",
    "Mode de paiement": "طريقة الدفع",
    "Espèces": "نقداً",
    "Virement": "تحويل بنكي",
    "Date": "التاريخ",
    "Date de paiement": "تاريخ الدفع",
    "Date d'inscription": "تاريخ التسجيل",
    "Date d'embauche": "تاريخ التوظيف",
    "Date début": "تاريخ البداية",
    "Date fin": "تاريخ النهاية",
    "Heure début": "وقت البداية",
    "Heure fin": "وقت النهاية",
    "Professeur": "الأستاذ",
    "Groupe / Classe": "الفوج / القسم",
    "Présents / Total": "الحاضرون / المجموع",
    "Ouverte": "مفتوحة",
    "Clôturée": "مغلقة",
    "En cours": "جارية",
    "Annulée": "ملغاة",
    "Salaire de base (DA)": "الراتب الأساسي (د.ج)",
    "Salaire de base": "الراتب الأساسي",
    "Retenue par absence (DA)": "خصم الغياب (د.ج)",
    "Prime (DA)": "مكافأة (د.ج)",
    "Autres retenues (DA)": "خصومات أخرى (د.ج)",
    "Salaire net": "صافي الراتب",
    "Net à payer": "المبلغ الصافي للصرف",
    "Période": "الفترة",
    "Bonus": "مكافأة",
    "Déductions": "الخصومات",
    "Poste": "المنصب",
    "Employé": "الموظف",

    # SELECTIONS / MATIERES & NIVEAUX
    "Sciences": "العلوم",
    "Mathématiques": "الرياضيات",
    "Français": "الفرنسية",
    "Arabe": "العربية",
    "Anglais": "الإنجليزية",
    "Primaire": "ابتدائي",
    "Moyen": "متوسط",
    "Lycée": "ثانوي",
    "Lundi": "الإثنين",
    "Mardi": "الثلاثاء",
    "Mercredi": "الأربعاء",
    "Jeudi": "الخميس",
    "Vendredi": "الجمعة",
    "Samedi": "السبت",
    "Dimanche": "الأحد",

    # ACTIONS & GENERAL UI
    "Nouveau": "جديد",
    "Enregistrer": "حفظ",
    "Supprimer": "حذف",
    "Rechercher": "بحث",
    "Annuler": "إلغاء",
    "Confirmer": "تأكيد",
    "Imprimer": "طباعة",
    "Retour": "رجوع",
    "Actions": "إجراءات",
    "Filtres": "تصفية",
    "Grouper par": "تجميع حسب",
}

def translate_all():
    db_name = "odoo-test"
    registry = odoo.registry(db_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})

        for lang_code in ['ar', 'ar_001']:
            print(f"--- Translating for language: {lang_code} ---")

            # 1. Menus (ir.ui.menu)
            menus = env['ir.ui.menu'].search([])
            translated_menus_count = 0
            for menu in menus:
                name_fr = menu.with_context(lang='fr_FR').name or menu.name
                if name_fr in TR_MAP:
                    menu.with_context(lang=lang_code).write({'name': TR_MAP[name_fr]})
                    translated_menus_count += 1
                elif menu.name in TR_MAP:
                    menu.with_context(lang=lang_code).write({'name': TR_MAP[menu.name]})
                    translated_menus_count += 1
            print(f"Updated {translated_menus_count} menus")

            # 2. Field Labels (ir.model.fields)
            fields = env['ir.model.fields'].search([('model', 'like', 'winners.')])
            translated_fields_count = 0
            for field in fields:
                field_fr = field.with_context(lang='fr_FR').field_description or field.field_description
                if field_fr in TR_MAP:
                    field.with_context(lang=lang_code).write({'field_description': TR_MAP[field_fr]})
                    translated_fields_count += 1
                elif field.field_description in TR_MAP:
                    field.with_context(lang=lang_code).write({'field_description': TR_MAP[field.field_description]})
                    translated_fields_count += 1
            print(f"Updated {translated_fields_count} field descriptions")

            # 3. Actions (ir.actions.act_window)
            actions = env['ir.actions.act_window'].search([('res_model', 'like', 'winners.')])
            translated_actions_count = 0
            for act in actions:
                act_fr = act.with_context(lang='fr_FR').name or act.name
                if act_fr in TR_MAP:
                    act.with_context(lang=lang_code).write({'name': TR_MAP[act_fr]})
                    translated_actions_count += 1
                elif act.name in TR_MAP:
                    act.with_context(lang=lang_code).write({'name': TR_MAP[act.name]})
                    translated_actions_count += 1
            print(f"Updated {translated_actions_count} actions")

            # 4. Selection values (ir.model.fields.selection)
            selections = env['ir.model.fields.selection'].search([('field_id.model', 'like', 'winners.')])
            translated_selections_count = 0
            for sel in selections:
                name_fr = sel.with_context(lang='fr_FR').name or sel.name
                if name_fr in TR_MAP:
                    sel.with_context(lang=lang_code).write({'name': TR_MAP[name_fr]})
                    translated_selections_count += 1
                elif sel.name in TR_MAP:
                    sel.with_context(lang=lang_code).write({'name': TR_MAP[sel.name]})
                    translated_selections_count += 1
            print(f"Updated {translated_selections_count} selection options")

        cr.commit()
        print("SUCCESS! All Odoo DB translations committed successfully!")

if __name__ == "__main__":
    translate_all()
