# -*- coding: utf-8 -*-
"""
Service d'impression ESC/POS hybride ultra-fiable pour imprimante thermique (XP-80C / 80mm).

- Purge automatique des travaux bloqués dans le Spooler Windows.
- Écriture USB directe via libusb_package avec libération automatique des ressources.
- Fallback automatique win32print.
"""

import logging

_logger = logging.getLogger(__name__)

# Importation sécurisée de win32print
HAS_WIN32PRINT = False
try:
    import win32print
    HAS_WIN32PRINT = True
except ImportError:
    _logger.info("win32print non disponible sur ce système.")

# Importation sécurisée de libusb / pyusb
HAS_LIBUSB = False
try:
    import libusb_package
    import usb.core
    import usb.util
    HAS_LIBUSB = True
except ImportError:
    _logger.info("libusb_package ou pyusb non disponible.")

# ══════════════════════════════════════
# CONSTANTES ESC/POS (80mm)
# ══════════════════════════════════════

ESC = b'\x1b'
GS = b'\x1d'

INIT = ESC + b'@'
CENTER = ESC + b'\x61\x01'
LEFT = ESC + b'\x61\x00'
RIGHT = ESC + b'\x61\x02'

BOLD_ON = ESC + b'\x45\x01'
BOLD_OFF = ESC + b'\x45\x00'

DOUBLE_HEIGHT = ESC + b'\x21\x10'
DOUBLE_SIZE = ESC + b'\x21\x30'
NORMAL_SIZE = ESC + b'\x21\x00'

CUT = GS + b'\x56\x01'
LF = b'\n'

SEP_SINGLE = b'------------------------------------------------\n'
SEP_DOUBLE = b'================================================\n'
WIDTH = 48


def format_row(left_txt, right_txt, width=WIDTH):
    """Formatte une ligne avec texte à gauche et valeur alignée à droite sur 48 colonnes."""
    left_txt = str(left_txt)
    right_txt = str(right_txt)
    space_available = width - len(left_txt) - len(right_txt)
    if space_available < 1:
        return f"{left_txt[:width - len(right_txt) - 1]} {right_txt}\n"
    return f"{left_txt}{' ' * space_available}{right_txt}\n"


def encode_text(text):
    """Encode le texte en latin-1 avec remplacement propre des accents pour imprimante thermique."""
    if not text:
        return b''
    s = str(text)
    replacements = {
        'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
        'à': 'a', 'â': 'a', 'ä': 'a',
        'î': 'i', 'ï': 'i',
        'ô': 'o', 'ö': 'o',
        'ù': 'u', 'û': 'u', 'ü': 'u',
        'ç': 'c', 'É': 'E', 'È': 'E', 'À': 'A', 'Ç': 'C',
        '°': ' ', '’': "'", '…': '...'
    }
    for orig, repl in replacements.items():
        s = s.replace(orig, repl)
    return s.encode('latin-1', errors='replace')


# ══════════════════════════════════════
# MOTEUR D'IMPRESSION HYBRIDE ULTRA-ROBUSTE
# ══════════════════════════════════════

def send_escpos_print(commands, vendor_id=0x0483, product_id=0x5743, printer_name='XP-80C'):
    """
    Envoie les commandes ESC/POS à l'imprimante thermique.
    1. Purge la file Windows Spooler pour débloquer le port USB si nécessaire.
    2. Envoie l'impression directe via libusb_package + release_resources.
    3. Fallback win32print si besoin.
    """
    # 1. Purge de la file Spooler Windows si bloquée
    if HAS_WIN32PRINT:
        try:
            available = [p[2] for p in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)]
            for p_name in available:
                if any(kw in p_name.upper() for kw in ['XP-80', 'XP80', 'POS', 'THERMAL', '80C', 'XP']):
                    try:
                        h = win32print.OpenPrinter(p_name, {'DesiredAccess': win32print.PRINTER_ALL_ACCESS})
                        jobs = win32print.EnumJobs(h, 0, -1, 1)
                        if jobs:
                            _logger.info("Purge automatique de %d travaux bloqués dans Windows Spooler '%s'", len(jobs), p_name)
                            win32print.SetPrinter(h, 0, None, win32print.PRINTER_CONTROL_PURGE)
                        win32print.ClosePrinter(h)
                    except Exception as purge_err:
                        _logger.debug("Purge Spooler notice: %s", purge_err)
        except Exception:
            pass

    errors = []

    # 2. Impression USB direct via libusb_package
    if HAS_LIBUSB and vendor_id and product_id:
        try:
            backend = libusb_package.get_libusb1_backend()
            dev = usb.core.find(idVendor=vendor_id, idProduct=product_id, backend=backend)

            if dev is not None:
                try:
                    dev.set_configuration()
                except Exception:
                    pass

                try:
                    cfg = dev.get_active_configuration()
                    intf = cfg[(0, 0)]
                    ep = usb.util.find_descriptor(
                        intf,
                        custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT
                    )
                    if ep is not None:
                        ep.write(commands)
                        _logger.info("Impression USB directe réussie via libusb.")
                        return True
                    else:
                        errors.append("Endpoint OUT introuvable sur le périphérique USB.")
                finally:
                    try:
                        usb.util.dispose_resources(dev)
                    except Exception:
                        pass
            else:
                errors.append(f"Périphérique USB non trouvé ({hex(vendor_id)}:{hex(product_id)}).")
        except Exception as usb_err:
            _logger.warning("Impression USB directe échouée (%s), tentative via win32print...", usb_err)
            errors.append(f"USB direct: {usb_err}")

    # 3. Fallback win32print (Windows Spooler)
    if HAS_WIN32PRINT:
        try:
            available = [p[2] for p in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)]
            target = None

            if printer_name and printer_name in available:
                target = printer_name
            else:
                for p_name in available:
                    if any(kw in p_name.upper() for kw in ['XP-80', 'XP80', 'POS', 'THERMAL', '80C', 'XP']):
                        target = p_name
                        break

            if target:
                _logger.info("Impression ESC/POS via win32print sur '%s'", target)
                hPrinter = win32print.OpenPrinter(target)
                try:
                    win32print.StartDocPrinter(hPrinter, 1, ("ESC/POS Ticket", None, "RAW"))
                    win32print.StartPagePrinter(hPrinter)
                    win32print.WritePrinter(hPrinter, commands)
                    win32print.EndPagePrinter(hPrinter)
                    win32print.EndDocPrinter(hPrinter)
                    return True
                finally:
                    win32print.ClosePrinter(hPrinter)
            else:
                errors.append("Aucune imprimante thermiques trouvée dans le Spooler Windows.")
        except Exception as win_err:
            _logger.warning("win32print a échoué : %s", win_err)
            errors.append(f"Spooler Windows: {win_err}")

    err_detail = " | ".join(errors) if errors else "Module d'impression non disponible."
    raise Exception(f"Erreur d'impression : {err_detail}")


def get_printer(vendor_id, product_id):
    """Fonction de compatibilité : retourne un wrapper pour ep.write(commands)."""
    class USBPrinterWrapper:
        def __init__(self, v_id, p_id):
            self.v_id = v_id
            self.p_id = p_id

        def write(self, commands):
            send_escpos_print(commands, vendor_id=self.v_id, product_id=self.p_id)

    return USBPrinterWrapper(vendor_id, product_id)


def print_escpos(commands, vendor_id=None, product_id=None, printer_name=None):
    """Fonction principale d'impression ESC/POS."""
    return send_escpos_print(commands, vendor_id=vendor_id or 0x0483, product_id=product_id or 0x5743, printer_name=printer_name or 'XP-80C')


# ══════════════════════════════════════
# BON DE PAIEMENT ÉTUDIANT (Format 80mm)
# ══════════════════════════════════════

def build_bon_paiement(data):
    """Construit les commandes ESC/POS 80mm pour un bon de paiement étudiant."""
    commands = INIT

    # En-tête
    commands += CENTER + BOLD_ON + DOUBLE_HEIGHT
    commands += encode_text(data.get('academy_name', 'WINNERS ACADEMY')) + LF
    commands += NORMAL_SIZE + BOLD_OFF
    if data.get('branch_name'):
        commands += encode_text(f"Branche : {data['branch_name']}") + LF
    commands += BOLD_ON
    commands += encode_text('--- BON DE PAIEMENT ---') + LF
    commands += BOLD_OFF
    commands += LEFT + SEP_DOUBLE

    # Dates
    commands += encode_text(format_row("Date paiement", data.get('date', '')))
    if data.get('prochain_versement'):
        commands += BOLD_ON
        commands += encode_text(format_row("Prochain versement", data['prochain_versement']))
        commands += BOLD_OFF
    commands += SEP_SINGLE

    # Informations Étudiant & Groupe
    commands += encode_text(format_row("Etudiant", data.get('nom_etudiant', '')))
    if data.get('matiere'):
        commands += encode_text(format_row("Matiere", data['matiere']))
    if data.get('groupe'):
        commands += encode_text(format_row("Groupe", data['groupe']))
    if data.get('niveau'):
        commands += encode_text(format_row("Niveau", data['niveau']))
    commands += SEP_SINGLE

    # Montant & mode
    montant = data.get('montant', 0)
    commands += BOLD_ON
    commands += encode_text(format_row("MONTANT PAYE", f"{montant:,.0f} DA".replace(',', ' ')))
    commands += BOLD_OFF
    commands += encode_text(format_row("Mode de paiement", data.get('mode_paiement', 'Especes')))
    commands += SEP_SINGLE

    # Séances
    commands += encode_text(format_row("Seances achetees", str(data.get('seances_achetees', 0))))
    commands += BOLD_ON
    commands += encode_text(format_row("Seances restantes", str(data.get('seances_restantes', 0))))
    commands += BOLD_OFF
    commands += SEP_DOUBLE

    # Pied de page
    commands += CENTER
    if data.get('agent'):
        commands += encode_text(f"Agent : {data['agent']}") + LF
    commands += encode_text("Merci de votre confiance !") + LF
    commands += SEP_SINGLE

    # Sauts de ligne + Coupe
    commands += LF * 4
    commands += CUT

    return commands


# ══════════════════════════════════════
# BORDEREAU DE GAINS ENSEIGNANT (Format 80mm)
# ══════════════════════════════════════

def build_bordereau_enseignant(data):
    """Construit les commandes ESC/POS 80mm pour un bordereau de gains enseignant."""
    commands = INIT

    # En-tête
    commands += CENTER + BOLD_ON + DOUBLE_HEIGHT
    commands += encode_text(data.get('academy_name', 'WINNERS ACADEMY')) + LF
    commands += NORMAL_SIZE + BOLD_OFF
    if data.get('branch_name'):
        commands += encode_text(f"Branche : {data['branch_name']}") + LF
    commands += BOLD_ON
    commands += encode_text('--- BORDEREAU D\'ENSEIGNANT ---') + LF
    commands += BOLD_OFF
    commands += LEFT + SEP_DOUBLE

    # Infos enseignant & groupe
    if data.get('ref'):
        commands += encode_text(format_row("Reference", data['ref']))
    commands += encode_text(format_row("Enseignant", data.get('nom_enseignant', '')))
    commands += encode_text(format_row("Groupe", data.get('groupe', '')))
    if data.get('periode'):
        commands += encode_text(format_row("Periode", data['periode']))
    commands += encode_text(format_row("Date impression", data.get('date', '')))
    commands += SEP_SINGLE

    # Détails séances & étudiants
    commands += encode_text(format_row("Seances faites", str(data.get('seances_faites', 0))))
    if data.get('nb_etudiants'):
        commands += encode_text(format_row("Nombre d'etudiants", str(data['nb_etudiants'])))
    commands += encode_text(format_row("Prix / Seance", f"{data.get('prix_seance', 0):,.0f} DA".replace(',', ' ')))

    t_total = data.get('montant_total', 0)
    commands += encode_text(format_row("Total collecte", f"{t_total:,.0f} DA".replace(',', ' ')))
    commands += encode_text(format_row("Pourcentage Ens.", f"{data.get('pourcentage', 0)} %"))
    commands += SEP_DOUBLE

    # Part Enseignant uniquement (Pas de part d'école !)
    t_ens = data.get('montant_enseignant', 0)
    commands += BOLD_ON + DOUBLE_HEIGHT + CENTER
    commands += encode_text(f"PART ENSEIGNANT : {t_ens:,.0f} DA".replace(',', ' ')) + LF
    commands += NORMAL_SIZE + BOLD_OFF + CENTER
    if data.get('state_label'):
        commands += encode_text(f"Statut : {data['state_label']}") + LF
    commands += SEP_SINGLE

    commands += LF * 4
    commands += CUT

    return commands


# ══════════════════════════════════════
# BULLETIN DE SALAIRE (Format 80mm)
# ══════════════════════════════════════

def build_bordereau_salaire(data):
    """Construit les commandes ESC/POS 80mm pour un bulletin de salaire enseignant simplifié."""
    commands = INIT

    # En-tête
    commands += CENTER + BOLD_ON + DOUBLE_HEIGHT
    commands += encode_text(data.get('academy_name', 'WINNERS ACADEMY')) + LF
    commands += NORMAL_SIZE + BOLD_OFF
    if data.get('branch_name'):
        commands += encode_text(f"Branche : {data['branch_name']}") + LF
    commands += BOLD_ON
    commands += encode_text('--- BULLETIN DE SALAIRE ---') + LF
    commands += BOLD_OFF
    commands += LEFT + SEP_DOUBLE

    # Informations enseignant & date
    commands += encode_text(format_row("Enseignant", data.get('nom_employe', '')))
    commands += encode_text(format_row("Poste", data.get('poste', 'Enseignant')))
    if data.get('periode'):
        commands += encode_text(format_row("Periode de paie", data['periode']))
    commands += encode_text(format_row("Date d'emission", data.get('date', '')))
    commands += SEP_DOUBLE

    # Net à payer uniquement
    net = data.get('salaire_net', 0)
    commands += BOLD_ON + DOUBLE_HEIGHT + CENTER
    commands += encode_text(f"NET A PAYER : {net:,.0f} DA".replace(',', ' ')) + LF
    commands += NORMAL_SIZE + BOLD_OFF + CENTER
    if data.get('state_label'):
        commands += encode_text(f"Statut : {data['state_label']}") + LF
    commands += SEP_SINGLE

    # Sauts de ligne + Coupe
    commands += LF * 4
    commands += CUT

    return commands


# ══════════════════════════════════════
# TICKET DE TEST (Format 80mm)
# ══════════════════════════════════════

def build_test_ticket(academy_name, date_str):
    """Construit un ticket de test ESC/POS 80mm."""
    commands = INIT
    commands += CENTER + BOLD_ON + DOUBLE_HEIGHT
    commands += encode_text(academy_name or 'WINNERS ACADEMY') + LF
    commands += NORMAL_SIZE + BOLD_OFF
    commands += SEP_DOUBLE
    commands += BOLD_ON
    commands += encode_text('--- TEST IMPRESSION 80MM ---') + LF
    commands += BOLD_OFF
    commands += SEP_DOUBLE
    commands += LEFT
    commands += encode_text(format_row("Imprimante", "XP-80C (USB Direct / Purge OK)"))
    commands += encode_text(format_row("Largeur papier", "80mm (48 colonnes)"))
    commands += encode_text(format_row("Date du test", date_str))
    commands += SEP_SINGLE
    commands += CENTER
    commands += encode_text("Test reussi avec succes !") + LF
    commands += SEP_DOUBLE
    commands += LF * 4
    commands += CUT
    return commands
