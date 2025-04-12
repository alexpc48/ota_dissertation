import sqlite3
db_connection = sqlite3.connect('client_windows_ota_updates.db')
cursor = db_connection.cursor()
ENCRYPTION_ALGORITHM = 'aes_256'  # Example value, replace with your actual algorithm
aes_key = (cursor.execute(f"SELECT {ENCRYPTION_ALGORITHM} FROM cryptographic_data LIMIT 1")).fetchone()[0]
db_connection.close()

print(aes_key)