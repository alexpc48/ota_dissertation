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

    # Network
    # server_ip, server_port = '192.168.225.97', 50097
    # windows_ip, windows_port = '192.168.225.150', 50150
    # linux_ip, linux_port = '192.168.225.69', 50069

    # Local
    server_ip, server_port = '127.0.0.1', 50097
    windows_ip, windows_port = '127.0.0.1', 50150
    linux_ip, linux_port = '127.0.0.1', 50069

    print("Setting up server database ...")
    db_connection = sqlite3.connect("..\\server_ota_updates.db")
    cursor = db_connection.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS vehicles (
                    vehicles_entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vehicle_id TEXT,
                    update_readiness_status BOOLEAN,
                    update_id INTEGER REFERENCES updates(update_id),
                    vehicle_ip TEXT,
                    vehicle_port INTEGER
                    )''') # TODO: Add cryptographic data
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS updates (
                    update_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    update_version TEXT,
                    update_file BLOB
                    )''')
    

    print("Adding data to the database ...")
    # Example vehicle (management PC)
    # cursor.execute('''INSERT INTO vehicles (vehicle_id, update_readiness_status, update_id, vehicle_ip, vehicle_port)
    #                 VALUES (?, ?, ?, ?, ?)''',
    #                 ('5B854E74-E19A-11E5-9C43-BC00007E0000', False, 1,'192.168.225.200', 50200))
    
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
    
    # Example updates
    file_data, _ = get_update_file('updates\\snoopy.png')
    cursor.execute('''INSERT INTO updates (update_version, update_file)
                    VALUES (?, ?)''',
                    ('1.0.0.png', file_data))
    file_data, _ = get_update_file('updates\\dban.iso')
    cursor.execute('''INSERT INTO updates (update_version, update_file)
                    VALUES (?, ?)''',
                    ('1.0.1.iso', file_data))
    file_data, _ = get_update_file('updates\\router_firmware.w')
    cursor.execute('''INSERT INTO updates (update_version, update_file)
                    VALUES (?, ?)''',
                    ('1.0.2.w', file_data))
    file_data, _ = get_update_file('updates\\popeye.png')
    cursor.execute('''INSERT INTO updates (update_version, update_file)
                    VALUES (?, ?)''',
                    ('1.0.3.png', file_data))

    db_connection.commit()
    db_connection.close()
    print("Server database setup complete.")












    print("Setting up client Windows database ...")
    db_connection = sqlite3.connect("..\\client_windows_ota_updates.db")
    cursor = db_connection.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS network_information (
                    network_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    server_ip TEXT,
                    server_port INTEGER
                    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS update_information (
                    update_entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    update_version TEXT,
                    update_file BLOB,
                    update_readiness_status BOOLEAN
                    )''')
    
    
    # cursor.execute('''CREATE TABLE IF NOT EXISTS cryptographic_data (
    #                 )''')

    print("Adding data to the database ...")
    cursor.execute('''INSERT INTO network_information (server_ip, server_port)
                    VALUES (?, ?)''',
                    (server_ip, server_port))
    
    file_data, _ = get_update_file('updates\\snoopy.png')
    cursor.execute('''INSERT INTO update_information (update_version, update_file, update_readiness_status)
                    VALUES (?, ?, ?)''',
                    ('1.0.2.png', file_data, False))
    
    db_connection.commit()
    db_connection.close()
    print("Client database setup complete.")












    
    print("Setting up client Linux database ...")
    db_connection = sqlite3.connect("..\\client_linux_ota_updates.db")
    cursor = db_connection.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS network_information (
                    network_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    server_ip TEXT,
                    server_port INTEGER
                    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS update_information (
                    update_entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    update_version TEXT,
                    update_file BLOB,
                    update_readiness_status BOOLEAN
                    )''')
    
    
    # cursor.execute('''CREATE TABLE IF NOT EXISTS cryptographic_data (
    #                 )''')

    print("Adding data to the database ...")
    cursor.execute('''INSERT INTO network_information (server_ip, server_port)
                    VALUES (?, ?)''',
                    (server_ip, server_port))
    
    file_data, _ = get_update_file('updates\\router_firmware.w')
    cursor.execute('''INSERT INTO update_information (update_version, update_file, update_readiness_status)
                    VALUES (?, ?, ?)''',
                    ('1.0.3.w', file_data, False))
    
    db_connection.commit()
    db_connection.close()
    print("Client database setup complete.")