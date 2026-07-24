# -*- coding: utf-8 -*-
import json
import odoo

config_file = r"C:\odoo17\odoo.conf"
odoo.tools.config.parse_config(["-c", config_file, "-d", "odoo-test"])

TR_MAP = {
    # MENUS & INTERFACE
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

def fix_table_column(cr, table_name, column_name):
    query = f"SELECT id, {column_name} FROM {table_name} WHERE {column_name} IS NOT NULL;"
    cr.execute(query)
    rows = cr.fetchall()
    updated_count = 0

    for row_id, val in rows:
        if not isinstance(val, dict):
            continue

        changed = False
        new_val = dict(val)

        # Determine original French/English text
        base_text = None
        for k in ['en_US', 'fr_FR', 'fr']:
            if k in new_val and isinstance(new_val[k], str) and new_val[k] in TR_MAP:
                base_text = new_val[k]
                break

        if not base_text:
            # Check if any value in the dict matches TR_MAP key
            for v in new_val.values():
                if isinstance(v, str) and v in TR_MAP:
                    base_text = v
                    break

        if base_text and base_text in TR_MAP:
            ar_text = TR_MAP[base_text]
            if new_val.get('ar') != ar_text or new_val.get('ar_001') != ar_text:
                new_val['ar'] = ar_text
                new_val['ar_001'] = ar_text
                new_val['fr_FR'] = base_text
                new_val['en_US'] = base_text
                changed = True

        if changed:
            update_query = f"UPDATE {table_name} SET {column_name} = %s WHERE id = %s;"
            cr.execute(update_query, (json.dumps(new_val, ensure_ascii=False), row_id))
            updated_count += 1

    print(f"[{table_name}.{column_name}] Updated {updated_count} rows out of {len(rows)}")

def main():
    db_name = "odoo-test"
    registry = odoo.registry(db_name)
    with registry.cursor() as cr:
        print("Starting JSONB direct translation fix...")
        fix_table_column(cr, "ir_ui_menu", "name")
        fix_table_column(cr, "ir_model_fields", "field_description")
        fix_table_column(cr, "ir_act_window", "name")
        fix_table_column(cr, "ir_model_fields_selection", "name")
        cr.commit()
        print("SUCCESS! All JSONB translations fixed and committed!")

if __name__ == "__main__":
    main()
