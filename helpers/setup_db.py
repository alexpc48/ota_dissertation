import sqlite3
import typing

# Get update file data in bytes
def get_update_file(file: str) -> typing.Tuple[bytes, int]:
    with open(file, 'rb') as file:
        file_data = file.read()
    return file_data, 0

# Sets up the data base for the system
# Not dynamically created to simulate real application
# Uses SQLite for simplicity as database tehcnology is out of scope
if __name__=='__main__':
    print("Setting up database ...")
    db_connection = sqlite3.connect("..\\ota_updates.db")
    cursor = db_connection.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS vehicles (
                    vehicles_entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vehicle_id TEXT,
                    update_readiness_status BOOLEAN,
                    update_id INTEGER REFERENCES updates(update_id),
                    vehicle_ip TEXT,
                    vehicle_port INTEGER,
                    server_ip TEXT,
                    server_port INTEGER
                    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS updates (
                    update_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    update_version TEXT,
                    update_file BLOB
                    )''')
    
    # TODO: Complete table for all required fields
    # cursor.execute('''CREATE TABLE IF NOT EXISTS authentication_keys (
    #                 vehicle_id INTEGER REFERENCES vehicles(vehicle_id),
    #                 aes_256_key BLOB,
    #                 ecc_384_pub_key BLOB,
    #                 ecc_384_priv_key BLOB,
    #                 )''')
    
    # cursor.execute('''CREATE TABLE IF NOT EXISTS update_history (
    #                vehicle_id INTEGER REFERENCES vehicles(vehicle_id),
    #                update_id INTEGER REFERENCES updates(update_id),
    #                update_status INTEGER,
    #                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    #                )''')
    
    # Add vehicles into the database
    server_ip, server_port = '192.168.225.97', 50097

    print("Adding data to the database ...")
    # Example vehicle (management PC)
    cursor.execute('''INSERT INTO vehicles (vehicle_id, update_readiness_status, update_id, vehicle_ip, vehicle_port, server_ip, server_port)
                    VALUES (?, ?, ?, ?, ?, ?, ?)''',
                    ('5B854E74-E19A-11E5-9C43-BC00007E0000', False, 1,'192.168.225.200', 50200, server_ip, server_port))
    
    # Linux laptop
    # UUID = c42157c2-9526-b07c-7e43-b4a9fc957957
    cursor.execute('''INSERT INTO vehicles (vehicle_id, update_readiness_status, update_id, vehicle_ip, vehicle_port, server_ip, server_port)
                    VALUES (?, ?, ?, ?, ?, ?, ?)''',
                    ('C42157C2-9526-B07C-7E43-B4A9FC957957', False, 2, '192.168.225.69', 50069, server_ip, server_port))

    # Windows laptop
    # UUID = CE41D0EA-C52B-E941-9F86-60F4FAF5CD8A
    cursor.execute('''INSERT INTO vehicles (vehicle_id, update_readiness_status, update_id, vehicle_ip, vehicle_port, server_ip, server_port)
                    VALUES (?, ?, ?, ?, ?, ?, ?)''',
                    ('C42157C2-9526-B07C-7E43-B4A9FC957957', True, 3, '192.168.225.150', 50150, server_ip, server_port))
    
    # Example updates
    file_data, _ = get_update_file('updates\\snoopy.png')
    cursor.execute('''INSERT INTO updates (update_version, update_file)
                    VALUES (?, ?)''',
                    ('1.0.0.png', file_data))
    file_data, _ = get_update_file('updates\\popeye.png')
    cursor.execute('''INSERT INTO updates (update_version, update_file)
                    VALUES (?, ?)''',
                    ('1.0.1.png', file_data))
    file_data, _ = get_update_file('updates\\dban.iso')
    cursor.execute('''INSERT INTO updates (update_version, update_file)
                    VALUES (?, ?)''',
                    ('1.0.2.iso', file_data))
    file_data, _ = get_update_file('updates\\router_firmware.w')
    cursor.execute('''INSERT INTO updates (update_version, update_file)
                    VALUES (?, ?)''',
                    ('1.0.3.w', file_data))

    db_connection.commit()
    db_connection.close()
    print("Database setup complete.")