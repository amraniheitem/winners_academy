import sys
import odoo
from odoo import api, SUPERUSER_ID

config_file = r"C:\odoo17\odoo.conf"
odoo.tools.config.parse_config(["-c", config_file, "-d", "odoo-test"])

# Comprehensive Translation Map
TR_MAP = {
    # TOP NAVBAR & MAIN MENUS
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
    "Specialty": "المادة",
    "Spécialité": "المادة",
    "Téléphone": "الهاتف",
    "Téléphone tuteur": "هاتف الولي",
    "Adresse": "العنوان",
    "Statut": "الحالة",
    "Statut d'inscription": "حالة الاشتراك",
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

    # SELECTIONS / MATIERES & NIVEAUX & SUBJECTS
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

def force_translate():
    db_name = "odoo-test"
    registry = odoo.registry(db_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})

        # Ensure 'ar' and 'ar_001' active in res.lang
        for lang_code in ['ar', 'ar_001']:
            lang_rec = env['res.lang'].search([('code', '=', lang_code)])
            if lang_rec and not lang_rec.active:
                lang_rec.active = True
                print(f"Activated language: {lang_code}")

        target_langs = ['ar', 'ar_001']

        for lang_code in target_langs:
            print(f"\n==========================================")
            print(f"   TRANSLATING DATABASE FOR: {lang_code}")
            print(f"==========================================")

            # 1. MENUS
            all_menus = env['ir.ui.menu'].search([])
            m_count = 0
            for menu in all_menus:
                # get original french name or current name
                fr_name = menu.with_context(lang='fr_FR').name or menu.name
                if fr_name in TR_MAP:
                    menu.with_context(lang=lang_code).write({'name': TR_MAP[fr_name]})
                    m_count += 1
                elif menu.name in TR_MAP:
                    menu.with_context(lang=lang_code).write({'name': TR_MAP[menu.name]})
                    m_count += 1
            print(f"[+] Translated {m_count} menus into {lang_code}")

            # 2. FIELDS (ir.model.fields)
            all_fields = env['ir.model.fields'].search([])
            f_count = 0
            for field in all_fields:
                fr_desc = field.with_context(lang='fr_FR').field_description or field.field_description
                if fr_desc in TR_MAP:
                    field.with_context(lang=lang_code).write({'field_description': TR_MAP[fr_desc]})
                    f_count += 1
                elif field.field_description in TR_MAP:
                    field.with_context(lang=lang_code).write({'field_description': TR_MAP[field.field_description]})
                    f_count += 1
            print(f"[+] Translated {f_count} fields into {lang_code}")

            # 3. ACTIONS (ir.actions.act_window)
            all_actions = env['ir.actions.act_window'].search([])
            a_count = 0
            for act in all_actions:
                fr_act = act.with_context(lang='fr_FR').name or act.name
                if fr_act in TR_MAP:
                    act.with_context(lang=lang_code).write({'name': TR_MAP[fr_act]})
                    a_count += 1
                elif act.name in TR_MAP:
                    act.with_context(lang=lang_code).write({'name': TR_MAP[act.name]})
                    a_count += 1
            print(f"[+] Translated {a_count} actions into {lang_code}")

            # 4. SELECTION OPTIONS (ir.model.fields.selection)
            all_sel = env['ir.model.fields.selection'].search([])
            s_count = 0
            for sel in all_sel:
                fr_sel = sel.with_context(lang='fr_FR').name or sel.name
                if fr_sel in TR_MAP:
                    sel.with_context(lang=lang_code).write({'name': TR_MAP[fr_sel]})
                    s_count += 1
                elif sel.name in TR_MAP:
                    sel.with_context(lang=lang_code).write({'name': TR_MAP[sel.name]})
                    s_count += 1
            print(f"[+] Translated {s_count} selection values into {lang_code}")

        # Clean web client translation cache by clearing ir.ui.view & menu caches
        env.registry.clear_caches()
        cr.commit()
        print("\nSUCCESS: All translations successfully committed to Odoo 17 database!")

if __name__ == "__main__":
    force_translate()
