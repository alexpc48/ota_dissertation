# import sqlite3
# db_connection = sqlite3.connect('..\\server_ota_updates.db')
# cursor = db_connection.cursor()
# blah = 'ed25519_private_key'
# blah = (cursor.execute(f"SELECT {blah} FROM cryptographic_data WHERE cryptographic_entry_id = 1")).fetchone()
# db_connection.close()

# print(blah)



import sqlite3
from cryptography.hazmat.primitives.asymmetric import ed25519

# Server side
payload = b'Hello, World!'
db_connection = sqlite3.connect('..\\server_ota_updates.db')
cursor = db_connection.cursor()
alg = 'ed25519'
ret = (cursor.execute(f"SELECT {alg}_private_key FROM cryptographic_data WHERE cryptographic_entry_id = 1")).fetchone()
db_connection.close()
svr_pri = ed25519.Ed25519PrivateKey.from_private_bytes(ret[0])
sig = svr_pri.sign(payload)
print(sig)

# Client side
payload = b'Hello, World!'
db_connection = sqlite3.connect('..\\client_windows_ota_updates.db')
cursor = db_connection.cursor()
alg = 'ed25519'
ret = (cursor.execute(f"SELECT server_{alg}_public_key FROM cryptographic_data WHERE cryptographic_entry_id = 1")).fetchone()
db_connection.close()
svr_pub = ed25519.Ed25519PublicKey.from_public_bytes(ret[0])
svr_pub.verify(sig, payload)
print("Signature verified successfully!")