# -*- coding: utf-8 -*-
import sys
import json
import re
import odoo

sys.stdout.reconfigure(encoding='utf-8')

config_file = r"C:\odoo17\odoo.conf"
odoo.tools.config.parse_config(["-c", config_file])

# ═══════════════════════════════════════════════════════════════
# COMPLETE TRANSLATION MAP  — Every visible French string → Arabic
# ═══════════════════════════════════════════════════════════════
TR_MAP = {
    # ── TOP NAVBAR & MAIN MENUS ──
    "Winners Academy": "أكاديمية وينرز",
    "Personnes": "الأشخاص",
    "Employés": "الموظفون",
    "Étudiants": "الطلاب والمسجلون",
    "Enseignants": "الأساتذة والمحاضرون",
    "Paiements": "المدفوعات",
    "Salaires": "الرواتب",
    "Bordereaux enseignant": "كشوف الأساتذة",
    "Bordereaux enseignants": "كشوف الأساتذة",
    "Transactions traitées": "المعاملات المعالجة",
    "Présences": "الحضور",
    "Présences du jour": "حضور اليوم",
    "Feuilles de présence": "قوائم الحضور",
    "Séances": "الحصص",
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
    "Créneaux horaires": "الفترات الزمنية",
    "Finance": "المالية",
    "Emploi des séances": "برنامج الحصص",
    "Liste des salles": "قائمة القاعات",
    "Bordereau de Salaire": "كشف الراتب",
    "Imprimer Bordereau": "طباعة الكشف",
    "Imprimer Bon": "طباعة السند",
    "Bon de Paiement": "سند الدفع",

    # ── ATTENDANCE / PRÉSENCES MODULE ──
    "Liste des étudiants": "قائمة الطلاب",
    "Audit de clôture": "تقرير الإغلاق",
    "Cliquez sur Présent ou En retard pour valider la présence de l'étudiant. Cela décompte automatiquement une séance de son abonnement.":
        "انقر على حاضر أو متأخر لتأكيد حضور الطالب. يتم خصم حصة تلقائياً من اشتراكه.",
    "Feuille de Présence": "ورقة الحضور",
    "Log de synchronisation": "سجل المزامنة",
    "Log Syncro ZKTeco": "سجل مزامنة البصمة",
    "Synchronisation ZKTeco": "مزامنة البصمة",
    "Anomalies": "الشذوذات",
    "Anomalie": "شذوذ",
    "Présent": "حاضر",
    "Present": "حاضر",
    "Absent": "غائب",
    "En retard": "متأخر",
    "Manuel": "يدوي",
    "ZKTeco K60": "بصمة ZKTeco K60",
    "Source": "المصدر",
    "UID Pointeuse": "معرف البصمة (UID)",
    "Empreinte associée": "بصمة مرتبطة",
    "Aucune empreinte associée": "لا توجد بصمة مرتبطة",
    "Associer une empreinte": "ربط بصمة",
    "Dissocier l'empreinte": "فك ربط البصمة",
    "Biométrie": "البصمة",
    "UID sur la pointeuse": "المعرف على جهاز البصمة",
    "Nom sur la pointeuse": "الاسم على جهاز البصمة",

    # ── FIELDS & HEADERS ──
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
    "Date et heure": "التاريخ والوقت",
    "Date de paiement": "تاريخ الدفع",
    "Date d'inscription": "تاريخ التسجيل",
    "Date d'embauche": "تاريخ التوظيف",
    "Date début": "تاريخ البداية",
    "Début de période": "بداية الفترة",
    "Date fin": "تاريخ النهاية",
    "Fin de période": "نهاية الفترة",
    "Heure début": "وقت البداية",
    "Heure fin": "وقت النهاية",
    "Professeur": "الأستاذ",
    "Enseignant": "الأستاذ",
    "Groupe / Classe": "الفوج / القسم",
    "Présents / Total": "الحاضرون / المجموع",
    "Ouverte": "مفتوحة",
    "Clôturée": "مغلقة",
    "En cours": "جارية",
    "Annulée": "ملغاة",
    "Salaire de base (DA)": "الراتب الأساسي (د.ج)",
    "Salaire de base": "الراتب الأساسي",
    "Retenue par absence (DA)": "خصم الغياب (د.ج)",
    "Retenue absences (DA)": "خصم الغيابات (د.ج)",
    "Prime (DA)": "مكافأة (د.ج)",
    "Autres retenues (DA)": "خصومات أخرى (د.ج)",
    "Salaire net (DA)": "صافي الراتب (د.ج)",
    "Salaire net": "صافي الراتب",
    "Net à payer": "المبلغ الصافي للصرف",
    "Période": "الفترة",
    "Bonus": "مكافأة",
    "Déductions": "الخصومات",
    "Poste": "المنصب",
    "Employé": "الموظف",
    "Compte utilisateur": "حساب المستخدم",
    "Élèves": "التلاميذ",
    "Nombre max d'élèves": "العدد الأقصى للتلاميذ",
    "Nombre d'élèves": "عدد التلاميذ",
    "Nom de la branche": "اسم الفرع",
    "Nom de la salle": "اسم القاعة",
    "Capacité (places)": "الطاقة الاستيعابية (مقعد)",
    "Capacité": "السعة",
    "Étage": "الطابق",
    "Équipements": "التجهيزات",
    "Disponible": "متوفر",
    "Jour": "اليوم",
    "Notes": "ملاحظات",
    "Référence": "المرجع",
    "Nom de la configuration": "اسم الإعداد",
    "Imprimante Principale": "الطابعة الرئيسية",
    "Vendor ID (HEX)": "معرف المصنّع (HEX)",
    "Product ID (HEX)": "معرف المنتج (HEX)",
    "Nom de l'académie": "اسم الأكاديمية",
    "Nom de la branche": "اسم الفرع",
    "Par défaut": "افتراضي",
    "Heures supplémentaires": "ساعات إضافية",
    "Taux horaire supp. (DA/h)": "أجرة الساعة الإضافية (د.ج/سا)",
    "Montant heures supp. (DA)": "مبلغ الساعات الإضافية (د.ج)",
    "Justification prime": "تبرير المكافأة",
    "Justification retenues": "تبرير الخصومات",
    "Validé par": "صادق عليه",

    # ── FORM HEADERS ──
    "Informations du paiement": "معلومات الدفع",
    "Informations personnelles": "المعلومات الشخصية",
    "Informations générales": "معلومات عامة",
    "Informations scolaires": "المعلومات الدراسية",
    "Détails": "التفاصيل",
    "Affectation": "التعيين",
    "Photo & Contact parent": "الصورة ومعلومات الولي",
    "Détails de l'association": "تفاصيل الربط",
    "Planification et localisation": "التخطيط والمكان",

    # ── SELECTIONS ──
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
    "Primaire 1": "ابتدائي 1",
    "Primaire 2": "ابتدائي 2",
    "Primaire 3": "ابتدائي 3",
    "Primaire 4": "ابتدائي 4",
    "Primaire 5": "ابتدائي 5",
    "CEM 1": "متوسط 1",
    "CEM 2": "متوسط 2",
    "CEM 3": "متوسط 3",
    "CEM 4": "متوسط 4",
    "Lycée 1": "ثانوي 1",
    "Lycée 2": "ثانوي 2",
    "Lycée 3": "ثانوي 3",
    "Planifiee": "مبرمجة",
    "Terminee": "منتهية",
    "Annulee": "ملغاة",
    "Brouillon": "مسودة",
    "Confirmé": "مؤكد",
    "Validé": "مؤكد",
    "Payé": "مدفوع",
    "Non traité": "غير معالج",
    "Non traite": "غير معالج",
    "Traité": "معالج",
    "Traite": "معالج",
    "Chaque 4 seances": "كل 4 حصص",
    "Mensuel": "شهري",
    "Alerte": "تنبيه",
    "Expiré": "منتهي",
    "Suspendu": "موقوف",
    "Aucune séance restante dans ce groupe": "لا توجد حصص متبقية في هذا الفوج",
    "Pas d'inscription dans ce groupe": "لا يوجد تسجيل في هذا الفوج",
    "Aucune feuille de présence trouvée": "لم يتم العثور على ورقة حضور",
    "Hors fenêtre d'acceptation": "خارج نافذة القبول",
    "UID inconnu (non associé à un étudiant)": "معرف غير معروف (غير مرتبط بطالب)",
    "UID inconnu": "معرف غير معروف",
    "Accepté (marqué présent)": "مقبول (مسجل حاضر)",
    "Doublon ignoré": "تكرار تم تجاهله",
    "Anomalie créée": "تم إنشاء شذوذ",
    "Overdue": "متأخر",
    "Today": "اليوم",
    "Planned": "مخطط",
    "Alert": "تنبيه",
    "Error": "خطأ",

    # ── BUTTONS ──
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
    "Tester l'impression": "اختبار الطباعة",
    "Créer un compte utilisateur": "إنشاء حساب مستخدم",
    "Recalculer": "إعادة الحساب",
    "Valider": "تأكيد",
    "Marquer payé": "تحديد كمدفوع",
    "Réouvrir": "إعادة فتح",

    # ── EMPTY STATE MESSAGES ──
    "Enregistrer un nouveau paiement": "تسجيل دفع جديد",
    "Ajouter un nouvel enseignant": "إضافة أستاذ جديد",
    "Inscrire un nouvel étudiant": "تسجيل طالب جديد",
    "Créer une nouvelle branche": "إنشاء فرع جديد",
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

        base_text = None
        for k in ['en_US', 'fr_FR', 'fr']:
            if k in new_val and isinstance(new_val[k], str) and new_val[k] in TR_MAP:
                base_text = new_val[k]
                break

        if not base_text:
            for v in new_val.values():
                if isinstance(v, str) and v in TR_MAP:
                    base_text = v
                    break

        if base_text and base_text in TR_MAP:
            ar_text = TR_MAP[base_text]
            new_val['ar'] = ar_text
            new_val['ar_001'] = ar_text
            if 'fr_FR' not in new_val:
                new_val['fr_FR'] = base_text
            changed = True

        if changed:
            update_query = f"UPDATE {table_name} SET {column_name} = %s WHERE id = %s;"
            cr.execute(update_query, (json.dumps(new_val, ensure_ascii=False), row_id))
            updated_count += 1

    print(f"[{table_name}.{column_name}] Updated {updated_count}/{len(rows)} rows")


def fix_view_archs(cr):
    cr.execute("SELECT id, arch_db FROM ir_ui_view WHERE arch_db IS NOT NULL;")
    rows = cr.fetchall()
    updated_count = 0

    for view_id, arch_db in rows:
        if not isinstance(arch_db, dict):
            continue

        new_arch = dict(arch_db)
        base_xml = new_arch.get('en_US') or new_arch.get('fr_FR') or next(iter(new_arch.values()), "")
        if not base_xml or not isinstance(base_xml, str):
            continue

        ar_xml = base_xml
        changed = False

        for fr_str, ar_str in TR_MAP.items():
            # Translate string="..." attributes
            old = f'string="{fr_str}"'
            if old in ar_xml:
                ar_xml = ar_xml.replace(old, f'string="{ar_str}"')
                changed = True
            # Translate <p> text content with class o_view_nocontent_smiling_face
            if f'>{fr_str}<' in ar_xml:
                ar_xml = ar_xml.replace(f'>{fr_str}<', f'>{ar_str}<')
                changed = True

        if changed:
            new_arch['ar'] = ar_xml
            new_arch['ar_001'] = ar_xml
            cr.execute("UPDATE ir_ui_view SET arch_db = %s WHERE id = %s;",
                        (json.dumps(new_arch, ensure_ascii=False), view_id))
            updated_count += 1

    print(f"[ir_ui_view.arch_db] Updated {updated_count}/{len(rows)} views")


def fix_arabic_numerals(cr):
    """Fix Arabic locale to use Western numerals (123) instead of Eastern (١٢٣)."""
    # Update res_lang for ar and ar_001
    for lang_code in ['ar', 'ar_001']:
        cr.execute("""
            UPDATE res_lang SET
                date_format = '%%d/%%m/%%Y',
                time_format = '%%H:%%M:%%S',
                decimal_point = '.',
                thousands_sep = ',',
                grouping = '[3,0]'
            WHERE code = %s;
        """, (lang_code,))
    print("[res_lang] Fixed Arabic locale to use Western numerals and dd/mm/yyyy format")


def grant_admin_role(cr, env):
    """Grant Super Admin role to user admin (ID 2)."""
    admin_user = env['res.users'].browse(2)
    if admin_user.exists():
        admin_user.write({'winners_role': 'super_admin'})
        admin_user._sync_winners_groups()
        print("[res.users] Granted Super Admin role to user admin (ID 2)")


def main():
    db_name = odoo.tools.config['db_name'] or "winners_db"
    print(f"Targeting database: {db_name}")
    registry = odoo.registry(db_name)
    with registry.cursor() as cr:
        env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
        print("=" * 60)
        print("  MASTER i18n & ROLES FIX — All tables + Views + Admin Role")
        print("=" * 60)

        grant_admin_role(cr, env)
        fix_table_column(cr, "ir_ui_menu", "name")
        fix_table_column(cr, "ir_model_fields", "field_description")
        fix_table_column(cr, "ir_model_fields", "help")
        fix_table_column(cr, "ir_act_window", "name")
        fix_table_column(cr, "ir_act_window", "help")
        fix_table_column(cr, "ir_model_fields_selection", "name")
        fix_view_archs(cr)
        fix_arabic_numerals(cr)

        cr.commit()
        print("\n✅ ALL DONE! Restart Odoo and refresh the browser.")


if __name__ == "__main__":
    main()
