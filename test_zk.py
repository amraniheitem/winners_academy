from test_zk import ZK

zk = ZK('192.168.1.150', port=4370, timeout=5, password=0)
conn = zk.connect()
print("Connecté !")
print("Firmware:", conn.get_firmware_version())

users = conn.get_users()
for user in users:
    print(f"ID: {user.user_id}, Nom: {user.name}")

conn.disconnect()