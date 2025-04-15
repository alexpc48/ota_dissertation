import sqlite3
db_connection = sqlite3.connect('..\\server_ota_updates.db')
cursor = db_connection.cursor()
blah = 'CE41D0EA-C52B-E941-9F86-60F4FAF5CD8A'
blah = (cursor.execute(f"SELECT updates.update_version, vehicles.last_poll_time FROM vehicles JOIN updates ON vehicles.update_id = updates.update_id WHERE vehicles.vehicle_id = ?", (blah,))).fetchone()
db_connection.close()

print(blah)