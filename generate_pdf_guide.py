# -*- coding: utf-8 -*-
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')

html_content = r"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Manuel Technique & Scénario d'Installation Desktop Electron — Winners Academy</title>
    <style>
        @page {
            size: A4;
            margin: 20mm 15mm 20mm 15mm;
            @bottom-right {
                content: "Page " counter(page) " / " counter(pages);
                font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
                font-size: 9pt;
                color: #64748B;
            }
        }
        body {
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
            color: #1E293B;
            line-height: 1.6;
            font-size: 10.5pt;
        }
        .header-cover {
            text-align: center;
            border-bottom: 3px solid #1A4789;
            padding-bottom: 20px;
            margin-bottom: 25px;
        }
        .logo-title {
            color: #1A4789;
            font-size: 26pt;
            font-weight: bold;
            margin: 0;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .subtitle {
            color: #E6097D;
            font-size: 14pt;
            font-weight: 600;
            margin-top: 5px;
            margin-bottom: 10px;
        }
        .doc-meta {
            color: #64748B;
            font-size: 9.5pt;
        }
        h2 {
            color: #1A4789;
            font-size: 14pt;
            border-left: 4px solid #E6097D;
            padding-left: 10px;
            margin-top: 22px;
            margin-bottom: 10px;
            page-break-after: avoid;
        }
        h3 {
            color: #0F172A;
            font-size: 11.5pt;
            margin-top: 15px;
            margin-bottom: 8px;
            page-break-after: avoid;
        }
        p, li {
            margin-bottom: 6px;
        }
        ul, ol {
            margin-top: 5px;
            padding-left: 20px;
        }
        code, pre {
            font-family: 'Consolas', 'Courier New', monospace;
            background-color: #F1F5F9;
            color: #0F172A;
            border-radius: 4px;
        }
        pre {
            padding: 10px;
            border: 1px solid #E2E8F0;
            font-size: 9pt;
            white-space: pre-wrap;
            word-wrap: break-word;
            page-break-inside: avoid;
        }
        .user-mode-card {
            background-color: #ECFDF5;
            border: 2px solid #10B981;
            padding: 15px;
            border-radius: 8px;
            margin: 15px 0;
        }
        .user-mode-title {
            color: #065F46;
            font-size: 13pt;
            font-weight: bold;
            margin-top: 0;
        }
        .tip-box {
            background-color: #EFF6FF;
            border: 1px solid #BFDBFE;
            border-left: 4px solid #1A4789;
            padding: 10px 12px;
            margin: 12px 0;
            border-radius: 4px;
            font-size: 9.5pt;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 12px 0;
            font-size: 9.5pt;
        }
        th, td {
            border: 1px solid #CBD5E1;
            padding: 8px 10px;
            text-align: left;
        }
        th {
            background-color: #F8FAFC;
            color: #1A4789;
            font-weight: bold;
        }
        .page-break {
            page-break-before: always;
        }
    </style>
</head>
<body>

    <div class="header-cover">
        <h1 class="logo-title">WINNERS ACADEMY</h1>
        <div class="subtitle">Guide Complet d'Installation & Mode d'Emploi Desktop Native Electron</div>
        <div class="doc-meta">
            Architecture 100% Electron Desktop Autonome (Splash Screen, Windows Tray & Single Instance)<br>
            <strong>Version :</strong> 1.0.0 Desktop Executable | <strong>Mise à jour :</strong> Juillet 2026
        </div>
    </div>

    <div class="user-mode-card">
        <div class="user-mode-title">🖥️ EXPÉRIENCE CLIENT QUOTIDIENNE (100% ELECTRON NATIVE)</div>
        <p>Le client bénéficie d'une application autonome de bureau Windows :</p>
        <ul>
            <li>Double-clic sur l'icône <strong>Winners Academy</strong>.</li>
            <li>Splash screen d'accueil animé avec barre de chargement.</li>
            <li>Ouverture de l'application en plein écran native (sans barre d'adresse URL, sans onglets web).</li>
            <li>Services d'arrière-plan (Odoo 17 & Pont Pointeuse ZKTeco) gérés automatiquement.</li>
        </ul>
    </div>

    <h2>1. SCÉNARIO D'INSTALLATION CHEZ LE CLIENT (NOUVEAU PC)</h2>
    <ol>
        <li>Copier le fichier d'installation <code>Winners Academy Setup 1.0.0.exe</code> sur le PC du client.</li>
        <li>Lancer le fichier <code>Winners Academy Setup 1.0.0.exe</code> (Installateur 1-Clic).</li>
        <li>Le programme crée le raccourci Bureau <strong>Winners Academy</strong> et installe l'application.</li>
        <li>Pour une première installation de base de données, exécuter <code>installer_winners_academy.bat</code>.</li>
    </ol>

    <h2>2. PARAMÉTRAGE HARDWARE</h2>
    <h3>2.1 Pointeuse ZKTeco K60</h3>
    <p>Pointeuse configurée sur l'adresse IP fixe <code>192.168.1.201</code>, port <code>4370</code> via le pont Python ZK Bridge.</p>

    <h3>2.2 Imprimante Thermique USB (ESC/POS)</h3>
    <p>Détection automatique USB et impression directe des reçus et tickets d'abonnements.</p>

</body>
</html>
"""

html_file = r"C:\Users\dell\Desktop\guide_installation_temp.html"
pdf_file = r"C:\Users\dell\Desktop\Guide_Installation_Deploiement_Winners.pdf"

with open(html_file, "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"HTML guide written to {html_file}")

wkhtmltopdf_bin = r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"
if os.path.exists(wkhtmltopdf_bin):
    cmd = [wkhtmltopdf_bin, "--enable-local-file-access", "--page-size", "A4", html_file, pdf_file]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"PDF successfully updated at: {pdf_file}")
    else:
        print(f"Error generating PDF: {result.stderr}")
