@echo off
title Installation Automatique — Winners Academy Desktop
color 0A
echo =======================================================================
echo          INSTALLATEUR AUTOMATIQUE — WINNERS ACADEMY DESKTOP
echo =======================================================================
echo.
echo [1/4] Verification de l'environnement Python et PostgreSQL...
if not exist "C:\odoo17\venv\Scripts\python.exe" (
    echo [ERREUR] Python n'est pas installe dans C:\odoo17\venv. Veuillez executer l'installation prealable.
    pause
    exit /b 1
)

echo [2/4] Initialisation et installation des 16 modules custom Winners...
"C:\odoo17\venv\Scripts\python.exe" "C:\odoo17\odoo-bin" -c "C:\odoo17\odoo.conf" -d winners_db -i winners_auth,winners_branch,winners_student,winners_enrollment,winners_teacher,winners_room,winners_group,winners_schedule,winners_attendance,winners_payment,winners_salary,winners_desktop,winners_print,winners_dashboard,winners_tv,winners_theme

echo [3/4] Application des traductions bilingues et formatage des chiffres 123...
"C:\odoo17\venv\Scripts\python.exe" "C:\Users\dell\Desktop\winners\scratch_master_i18n_fix.py"

echo [4/4] Creation du raccourci Bureau Application Native (Mode 1-Clic)...
powershell -ExecutionPolicy Bypass -File "C:\Users\dell\Desktop\winners\create_desktop_shortcut.ps1"

echo.
echo =======================================================================
echo [SUCCES] L'installation de Winners Academy Desktop est terminee !
echo L'icone "Winners Academy" a ete creee sur votre Bureau Windows.
echo Le client peut simplement double-cliquer dessus pour travailler.
echo =======================================================================
pause
