# -*- coding: utf-8 -*-
"""
Script de diagnostic ZKTeco - Teste toute la chaîne
Lance ce script via: python diag_zk.py
Ou via odoo shell: python c:\odoo17\odoo-bin shell -d odoo-test < diag_zk.py
"""
import requests
import json
from datetime import datetime

BRIDGE_URL = "http://localhost:5000"

def test_bridge():
    print("=" * 60)
    print("DIAGNOSTIC ZK BRIDGE")
    print("=" * 60)

    # 1. Health check
    print("\n[1] Health check...")
    try:
        r = requests.get(f"{BRIDGE_URL}/", timeout=5)
        print(f"   Status: {r.status_code}")
        print(f"   Response: {r.json()}")
    except Exception as e:
        print(f"   ERREUR: {e}")
        return

    # 2. Device status
    print("\n[2] Device status...")
    try:
        r = requests.get(f"{BRIDGE_URL}/device/status", timeout=10)
        data = r.json()
        print(f"   Success: {data.get('success')}")
        if data.get('success'):
            d = data['data']
            print(f"   Connected: {d.get('connected')}")
            print(f"   Users: {d.get('user_count')}")
            print(f"   Transactions: {d.get('transaction_count')}")
        else:
            print(f"   Error: {data.get('error')}")
    except Exception as e:
        print(f"   ERREUR: {e}")

    # 3. Device users
    print("\n[3] Device users...")
    try:
        r = requests.get(f"{BRIDGE_URL}/device/users", timeout=10)
        data = r.json()
        if data.get('success'):
            users = data['data']['users']
            print(f"   {len(users)} utilisateur(s) sur la pointeuse:")
            for u in users:
                print(f"   - uid={u['uid']}, user_id={u['user_id']}, name={u['name']}")
        else:
            print(f"   Error: {data.get('error')}")
    except Exception as e:
        print(f"   ERREUR: {e}")

    # 4. Sync attendance
    print("\n[4] Sync attendance...")
    try:
        r = requests.post(f"{BRIDGE_URL}/device/sync_attendance", timeout=15)
        data = r.json()
        if data.get('success'):
            txns = data['data']['transactions']
            print(f"   {len(txns)} transaction(s):")
            for t in txns:
                print(f"   - user_id={t['user_id']}, timestamp={t['timestamp']}, uid={t.get('uid')}")
        else:
            print(f"   Error: {data.get('error')}")
    except Exception as e:
        print(f"   ERREUR: {e}")

    print("\n" + "=" * 60)
    print("FIN DIAGNOSTIC BRIDGE")
    print("=" * 60)


if __name__ == '__main__':
    test_bridge()
