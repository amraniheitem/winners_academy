# -*- coding: utf-8 -*-
"""
TEST DE VALIDATION AVANT LIVRAISON CLIENT
==========================================
Teste tous les scénarios et fonctionnalités du système.
"""
import requests
from datetime import datetime

BRIDGE_URL = "http://localhost:5000"
TESTS_PASSED = 0
TESTS_FAILED = 0
WARNINGS = []

def test(name, condition, detail=""):
    global TESTS_PASSED, TESTS_FAILED
    if condition:
        print(f"  [OK]   {name}")
        TESTS_PASSED += 1
    else:
        print(f"  [FAIL] {name} - {detail}")
        TESTS_FAILED += 1

def warn(msg):
    global WARNINGS
    WARNINGS.append(msg)
    print(f"  [WARN] {msg}")

print("=" * 60)
print("TEST DE VALIDATION COMPLET AVANT LIVRAISON")
print(f"Heure du test : {datetime.now()}")
print("=" * 60)

# 1. Service ZK Bridge
print("\n[1] SERVICE ZK BRIDGE (FLASK)")
try:
    r = requests.get(f"{BRIDGE_URL}/", timeout=5)
    test("Bridge accessible (HTTP 200)", r.status_code == 200)
    data = r.json()
    test("Bridge retourne success=True", data.get('success') == True)
    test("Version du service", data.get('data', {}).get('version') == '1.0.0')
except Exception as e:
    test("Bridge accessible", False, str(e))

# 2. Pointeuse ZKTeco
print("\n[2] CONNEXION POINTEUSE ZKTECO")
try:
    r = requests.get(f"{BRIDGE_URL}/device/status", timeout=15)
    test("Endpoint /device/status repond", r.status_code == 200)
    data = r.json()
    test("Pointeuse connectee", data.get('data', {}).get('connected') == True)
    user_count = data.get('data', {}).get('user_count', 0)
    test(f"Utilisateurs sur pointeuse ({user_count})", user_count > 0)
except Exception as e:
    test("Pointeuse accessible", False, str(e))

# 3. Odoo HTTP
print("\n[3] ODOO SERVER (HTTP)")
try:
    r = requests.get("http://localhost:8069/web/login", timeout=5)
    test("Odoo repond sur http://localhost:8069", r.status_code == 200)
except Exception as e:
    test("Odoo accessible", False, str(e))

# 4. Script Windows Startup
print("\n[4] SCRIPT DEMARRAGE AUTOMATIQUE (STARTUP)")
import os
startup_path = os.path.join(
    os.environ.get('APPDATA', ''),
    r"Microsoft\Windows\Start Menu\Programs\Startup",
    "start_zk_bridge.bat"
)
test("Script start_zk_bridge.bat existe", os.path.exists(startup_path), f"Introuvable: {startup_path}")
if os.path.exists(startup_path):
    with open(startup_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    test("Contient zk_bridge_service.py", "zk_bridge_service.py" in content)
    test("Contient executable Python", "python" in content.lower())

print("\n" + "=" * 60)
print(f"RESUME : {TESTS_PASSED} reussi(s), {TESTS_FAILED} echoue(s)")
if TESTS_FAILED == 0:
    print("TOUS LES TESTS PASSENT AVEC SUCCES !")
print("=" * 60)
