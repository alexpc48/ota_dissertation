# Helper script to set up the database for the OTA update system
# Uses example data

import sqlite3
import typing

# Gets the example update files data in bytes
def get_update_file(file: str) -> typing.Tuple[bytes, int]:
    with open(file, 'rb') as file:
        file_data = file.read()
    return file_data, 0

# Sets up the data base for the system
# Not dynamically created so it simulates real application (pre-made dataases)
# Uses SQLite for simplicity as database tehcnology is out of scope
# TODO: Add cryptographic data table to the database
if __name__=='__main__':

    # Running on network OTA
    # server_ip, server_port = '192.168.225.97', 50097
    # windows_ip, windows_port = '192.168.225.150', 50150
    # linux_ip, linux_port = '192.168.225.69', 50069

    # Running on local machine (testing)
    server_ip, server_port = '127.0.0.1', 50097
    windows_ip, windows_port = '127.0.0.1', 50150
    linux_ip, linux_port = '127.0.0.1', 50069

    print("Setting up server database ...")
    db_connection = sqlite3.connect("server_ota_updates.db")
    cursor = db_connection.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS network_information (
                    network_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    local_ip TEXT,
                    local_port INTEGER
                    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS vehicles (
                    vehicles_entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vehicle_id TEXT,
                    update_readiness_status BOOLEAN,
                    update_id INTEGER REFERENCES updates(update_id),
                    vehicle_ip TEXT,
                    vehicle_port INTEGER
                    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS updates (
                    update_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    update_version TEXT,
                    update_file BLOB
                    )''')
    
    print("Adding data to the server database ...")
   
    # Linux laptop
    # UUID = c42157c2-9526-b07c-7e43-b4a9fc957957
    cursor.execute('''INSERT INTO vehicles (vehicle_id, update_readiness_status, update_id, vehicle_ip, vehicle_port)
                    VALUES (?, ?, ?, ?, ?)''',
                    ('C42157C2-9526-B07C-7E43-B4A9FC957957', False, 2, linux_ip, linux_port))

    # Windows laptop
    # UUID = CE41D0EA-C52B-E941-9F86-60F4FAF5CD8A
    cursor.execute('''INSERT INTO vehicles (vehicle_id, update_readiness_status, update_id, vehicle_ip, vehicle_port)
                    VALUES (?, ?, ?, ?, ?)''',
                    ('CE41D0EA-C52B-E941-9F86-60F4FAF5CD8A', True, 3, windows_ip, windows_port))
    
    cursor.execute('''INSERT INTO network_information (local_ip, local_port)
                    VALUES (?, ?)''',
                    (server_ip, server_port))
    
    # Example updates
    file_data, _ = get_update_file('updates/snoopy.png')
    cursor.execute('''INSERT INTO updates (update_version, update_file)
                    VALUES (?, ?)''',
                    ('1.0.0.png', file_data))
    file_data, _ = get_update_file('updates/dban.iso')
    cursor.execute('''INSERT INTO updates (update_version, update_file)
                    VALUES (?, ?)''',
                    ('1.0.1.iso', file_data))
    file_data, _ = get_update_file('updates/router_firmware.w')
    cursor.execute('''INSERT INTO updates (update_version, update_file)
                    VALUES (?, ?)''',
                    ('1.0.2.w', file_data))
    file_data, _ = get_update_file('updates/popeye.png')
    cursor.execute('''INSERT INTO updates (update_version, update_file)
                    VALUES (?, ?)''',
                    ('1.0.3.png', file_data))
    file_data, _ = get_update_file('updates/bugs_bunny.jpg')
    cursor.execute('''INSERT INTO updates (update_version, update_file)
                    VALUES (?, ?)''',
                    ('1.0.4.jpg', file_data))

    db_connection.commit()
    db_connection.close()
    print("Server database setup complete.")













    print("Setting up client Windows database ...")
    db_connection = sqlite3.connect("client_windows_ota_updates.db")
    cursor = db_connection.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS network_information (
                    network_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    server_ip TEXT,
                    server_port INTEGER,
                    local_ip TEXT,
                    local_port INTEGER
                    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS update_information (
                    update_entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    update_version TEXT,
                    update_readiness_status BOOLEAN
                    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS update_downloads (
                    download_entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    update_version TEXT,
                    update_file BLOB
                    )''')
    
    print("Adding data to the Windows client database ...")
    cursor.execute('''INSERT INTO network_information (server_ip, server_port, local_ip, local_port)
                    VALUES (?, ?, ?, ?)''',
                    (server_ip, server_port, windows_ip, windows_port))
    
    file_data, _ = get_update_file('updates/snoopy.png')
    cursor.execute('''INSERT INTO update_information (update_version, update_readiness_status)
                    VALUES (?, ?)''',
                    ('1.0.2.png', False))
    
    db_connection.commit()
    db_connection.close()
    print("Windows client database setup complete.")













    print("Setting up client Linux database ...")
    db_connection = sqlite3.connect("client_linux_ota_updates.db")
    cursor = db_connection.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS network_information (
                    network_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    server_ip TEXT,
                    server_port INTEGER,
                    local_ip TEXT,
                    local_port INTEGER
                    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS update_information (
                    update_entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    update_version TEXT,
                    update_readiness_status BOOLEAN
                    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS update_downloads (
                    download_entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    update_version TEXT,
                    update_file BLOB
                    )''')

    print("Adding data to the Linux database ...")
    cursor.execute('''INSERT INTO network_information (server_ip, server_port, local_ip, local_port)
                    VALUES (?, ?, ?, ?)''',
                    (server_ip, server_port, linux_ip, linux_port))
    
    file_data, _ = get_update_file('updates/router_firmware.w')
    cursor.execute('''INSERT INTO update_information (update_version, update_readiness_status)
                    VALUES (?, ?)''',
                    ('1.0.3.w', False))
    
    db_connection.commit()
    db_connection.close()
    print("Linux client database setup complete.")