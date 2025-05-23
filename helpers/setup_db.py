# Helper script to set up the database for the OTA update system
# Uses example data

import sqlite3
import typing
import os
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from Crypto.Random import get_random_bytes
import shutil
from get_os_type import *

# Gets the example update files data in bytes
def get_update_file(file: str) -> typing.Tuple[bytes, int]:
    with open(file, 'rb') as file:
        file_data = file.read()
    return file_data, 0

# Converts \n to \r\n for same formatting across platforms
# Simple unix2dos implementation 
def convert_data_format(data: bytes) -> typing.Tuple[bytes, int]:
    data = data.decode('utf-8')
    data = data.replace('\n', '\r\n')
    data = data.encode('utf-8')
    return data, 0

# Sets up the data base for the system
# Not dynamically created so it simulates real application (pre-made dataases)
# Uses SQLite for simplicity as database tehcnology is out of scope
if __name__=='__main__':

    print("Setting networking information ...")


    # Change network information accordingly to use either on a custom local network, or on a singlular local machine
    # Change networking constants so ports match ones here
    # Running on network OTA
    # Pi as server
    # server_ip, server_port = '192.168.225.97', 50097
    # windows_ip, windows_port = '192.168.225.150', 50150
    # linux_ip, linux_port = '192.168.225.69', 50069
    # test_environment = False
    # pi_is_client = False

    # Running on network OTA
    # Pi as a client
    # server_ip, server_port = '192.168.225.69', 50069
    # windows_ip, windows_port = '192.168.225.150', 50150
    # linux_ip, linux_port = '192.168.225.97', 50097
    # test_environment = False
    # pi_is_client = True
    
    # Running on local machine (testing on development machine)
    server_ip, server_port = '127.0.0.1', 50069
    windows_ip, windows_port = '127.0.0.1', 50150
    linux_ip, linux_port = '127.0.0.1', 50097
    test_environment = True
    pi_is_client = False

    print("Networking information set.")

    print("Preparing example data ...")
    # Loads update files
    # Used to accomodate both Windows and Linux file paths
    os_type = get_os_type_func()
    if os_type == "Windows":
        file1 = 'updates\\snoopy.png'
        file2 = 'updates\\dban.iso'
        file3 = 'updates\\router_firmware.w'
        file4 = 'updates\\popeye.png'
        file5 = 'updates\\bugs_bunny.jpg'
        file6 = 'updates\\daffy_duck.png'
        # Copy example files to the install location to initialise it
        shutil.copyfile(file3, "install_location\\1.0.2.w")

    elif os_type == "Linux":
        file1 = 'updates/snoopy.png'
        file2 = 'updates/dban.iso'
        file3 = 'updates/router_firmware.w'
        file4 = 'updates/popeye.png'
        file5 = 'updates/bugs_bunny.jpg'
        file6 = 'updates/daffy_duck.png'
        # Copy example files to the install location to initialise it
        shutil.copyfile(file4, "install_location/1.0.3.png")

    # # Creates cryptographic material
    # # Ed25519 keys are used
    # Incorrect - each device creates own instance of keys
    # # Generates public and private keys for the server and clients
    # server_eddsa_private_key = Ed25519PrivateKey.generate()
    # server_eddsa_public_key = server_eddsa_private_key.public_key()
    # windows_eddsa_private_key = Ed25519PrivateKey.generate()
    # windows_eddsa_public_key = windows_eddsa_private_key.public_key()
    # linux_eddsa_private_key = Ed25519PrivateKey.generate()
    # linux_eddsa_public_key = linux_eddsa_private_key.public_key()
    # # Converts keys to bytes for storage in the database
    # server_eddsa_private_key = server_eddsa_private_key.private_bytes_raw()
    # server_eddsa_public_key = server_eddsa_public_key.public_bytes_raw()
    # windows_eddsa_private_key = windows_eddsa_private_key.private_bytes_raw()
    # windows_eddsa_public_key = windows_eddsa_public_key.public_bytes_raw()
    # linux_eddsa_private_key = linux_eddsa_private_key.private_bytes_raw()
    # linux_eddsa_public_key = linux_eddsa_public_key.public_bytes_raw()

    # Define the input directory
    input_dir = os.path.join("cryptographic_material")

    # Helper function to load raw key bytes from a .txt file
    def load_key_from_file(filename):
        with open(os.path.join(input_dir, filename), 'rb') as f:
            return f.read()

    # Load raw key bytes
    server_eddsa_private_key = load_key_from_file("server_private.txt")
    server_eddsa_public_key = load_key_from_file("server_public.txt")
    windows_eddsa_private_key = load_key_from_file("windows_private.txt")
    windows_eddsa_public_key = load_key_from_file("windows_public.txt")
    linux_eddsa_private_key = load_key_from_file("linux_private.txt")
    linux_eddsa_public_key = load_key_from_file("linux_public.txt")

    # Certificates and keys are pre-made and stored as files
    # In reality would be generated and signed by a CA
    # Different certificates are used for network-based OTA and local OTA for testing to enable context.check_hostname to work
    # New certificates were generated so the SAN was 127.0.0.1 when in testing
    if os_type == "Windows":
        aes_128_windows_client, _ = get_update_file("cryptographic_material\\aes_128_windows_client.key")
        aes_256_windows_client, _ = get_update_file("cryptographic_material\\aes_256_windows_client.key")
        aes_128_linux_client, _ = get_update_file("cryptographic_material\\aes_128_linux_client.key")
        aes_256_linux_client, _ = get_update_file("cryptographic_material\\aes_256_linux_client.key")
        root_ca, _ = get_update_file("cryptographic_material\\root_ca.pem")
        if test_environment == True:
            #print("Test environment")
            server_private_key, _ = get_update_file("cryptographic_material\\server_private_key_local_host.pem")
            server_certificate, _ = get_update_file("cryptographic_material\\server_certificate_local_host.pem")
            windows_client_private_key, _ = get_update_file("cryptographic_material\\windows_client_private_key_local_host.pem")
            windows_client_certificate, _ = get_update_file("cryptographic_material\\windows_client_certificate_local_host.pem")
            linux_client_private_key, _ = get_update_file("cryptographic_material\\linux_client_private_key_local_host.pem")
            linux_client_certificate, _ = get_update_file("cryptographic_material\\linux_client_certificate_local_host.pem")
        elif test_environment == False and pi_is_client == True:
            #print("Pi is client")
            server_private_key, _ = get_update_file("cryptographic_material\\server_private_key_pi_client.pem")
            server_certificate, _ = get_update_file("cryptographic_material\\server_certificate_pi_client.pem")
            windows_client_private_key, _ = get_update_file("cryptographic_material\\windows_client_private_key_pi_client.pem")
            windows_client_certificate, _ = get_update_file("cryptographic_material\\windows_client_certificate_pi_client.pem")
            linux_client_private_key, _ = get_update_file("cryptographic_material\\linux_client_private_key_pi_client.pem")
            linux_client_certificate, _ = get_update_file("cryptographic_material\\linux_client_certificate_pi_client.pem")
        else:
            #print("Pi is server")
            server_private_key, _ = get_update_file("cryptographic_material\\server_private_key.pem")
            server_certificate, _ = get_update_file("cryptographic_material\\server_certificate.pem")
            windows_client_private_key, _ = get_update_file("cryptographic_material\\windows_client_private_key.pem")
            windows_client_certificate, _ = get_update_file("cryptographic_material\\windows_client_certificate.pem")
            linux_client_private_key, _ = get_update_file("cryptographic_material\\linux_client_private_key.pem")
            linux_client_certificate, _ = get_update_file("cryptographic_material\\linux_client_certificate.pem")

        root_ca = root_ca.decode('utf-8')
        root_ca = root_ca.encode('utf-8')
        server_private_key = server_private_key.decode('utf-8')
        server_private_key = server_private_key.encode('utf-8')
        server_certificate = server_certificate.decode('utf-8')
        server_certificate = server_certificate.encode('utf-8')
        windows_client_private_key = windows_client_private_key.decode('utf-8')
        windows_client_private_key = windows_client_private_key.encode('utf-8')
        windows_client_certificate = windows_client_certificate.decode('utf-8')
        windows_client_certificate = windows_client_certificate.encode('utf-8')
        linux_client_private_key = linux_client_private_key.decode('utf-8')
        linux_client_private_key = linux_client_private_key.encode('utf-8')
        linux_client_certificate = linux_client_certificate.decode('utf-8')
        linux_client_certificate = linux_client_certificate.encode('utf-8')

    elif os_type == "Linux":
        aes_128_windows_client, _ = get_update_file("cryptographic_material/aes_128_windows_client.key")
        aes_256_windows_client, _ = get_update_file("cryptographic_material/aes_256_windows_client.key")
        aes_128_linux_client, _ = get_update_file("cryptographic_material/aes_128_linux_client.key")
        aes_256_linux_client, _ = get_update_file("cryptographic_material/aes_256_linux_client.key")
        root_ca, _ = get_update_file("cryptographic_material/root_ca.pem")

        if test_environment == True:
            #print("Test environment")
            server_private_key, _ = get_update_file("cryptographic_material/server_private_key_local_host.pem")
            server_certificate, _ = get_update_file("cryptographic_material/server_certificate_local_host.pem")
            windows_client_private_key, _ = get_update_file("cryptographic_material/windows_client_private_key_local_host.pem")
            windows_client_certificate, _ = get_update_file("cryptographic_material/windows_client_certificate_local_host.pem")
            linux_client_private_key, _ = get_update_file("cryptographic_material/linux_client_private_key_local_host.pem")
            linux_client_certificate, _ = get_update_file("cryptographic_material/linux_client_certificate_local_host.pem")
        elif test_environment == False and pi_is_client == True:
            #print("Pi is client")
            server_private_key, _ = get_update_file("cryptographic_material/server_private_key_pi_client.pem")
            server_certificate, _ = get_update_file("cryptographic_material/server_certificate_pi_client.pem")
            windows_client_private_key, _ = get_update_file("cryptographic_material/windows_client_private_key_pi_client.pem")
            windows_client_certificate, _ = get_update_file("cryptographic_material/windows_client_certificate_pi_client.pem")
            linux_client_private_key, _ = get_update_file("cryptographic_material/linux_client_private_key_pi_client.pem")
            linux_client_certificate, _ = get_update_file("cryptographic_material/linux_client_certificate_pi_client.pem")
        else:
            #print("Pi is server")
            server_private_key, _ = get_update_file("cryptographic_material/server_private_key.pem")
            server_certificate, _ = get_update_file("cryptographic_material/server_certificate.pem")
            windows_client_private_key, _ = get_update_file("cryptographic_material/windows_client_private_key.pem")
            windows_client_certificate, _ = get_update_file("cryptographic_material/windows_client_certificate.pem")
            linux_client_private_key, _ = get_update_file("cryptographic_material/linux_client_private_key.pem")
            linux_client_certificate, _ = get_update_file("cryptographic_material/linux_client_certificate.pem")

        root_ca, _ = convert_data_format(root_ca)
        server_private_key, _ = convert_data_format(server_private_key)
        server_certificate, _ = convert_data_format(server_certificate)
        windows_client_private_key, _ = convert_data_format(windows_client_private_key)
        windows_client_certificate, _ = convert_data_format(windows_client_certificate)
        linux_client_private_key, _ = convert_data_format(linux_client_private_key)
        linux_client_certificate, _ = convert_data_format(linux_client_certificate)

    print("Example data prepared.")

    print("Setting up server database ...")
    db_connection = sqlite3.connect("server_ota_updates.db")
    cursor = db_connection.cursor()

    print("Creating tables ...")
    
    # Network information for the server
    cursor.execute('''CREATE TABLE IF NOT EXISTS network_information (
                    network_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    local_ip TEXT,
                    local_port INTEGER,
                    identifier TEXT
                    )''')
    
    # In reality would just have a single symmetric and asymmetric key version
    # Stores symmetric keys and public keys for the clients
    cursor.execute('''CREATE TABLE IF NOT EXISTS vehicles (
                    vehicles_entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vehicle_id TEXT,
                    update_readiness_status BOOLEAN,
                    update_install_status BOOLEAN,
                    update_id INTEGER REFERENCES updates(update_id),
                    vehicle_ip TEXT,
                    vehicle_port INTEGER,
                    last_poll_time TIMESTAMP,
                    aes_128 BLOB,
                    aes_256 BLOB,
                    ed25519_public_key BLOB
                    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS updates (
                    update_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    update_version TEXT,
                    update_file BLOB
                    )''')
    
    # Cryptographic data specific to the server
    cursor.execute('''CREATE TABLE IF NOT EXISTS cryptographic_data (
                    cryptographic_entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ed25519_private_key BLOB,
                    ed25519_public_key BLOB,
                    server_private_key BLOB,
                    server_certificate BLOB,
                    root_ca BLOB
                    )''')
    
    print("Tables created.")
    
    print("Adding data to the server database ...")

    # Windows laptop
    # UUID = CE41D0EA-C52B-E941-9F86-60F4FAF5CD8A
    cursor.execute('''INSERT INTO vehicles (vehicle_id, update_readiness_status, update_install_status, update_id, vehicle_ip, vehicle_port, last_poll_time, aes_128, aes_256, ed25519_public_key)
                    VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?)''',
                    ('CE41D0EA-C52B-E941-9F86-60F4FAF5CD8A', True, True, 3, windows_ip, windows_port, aes_128_windows_client, aes_256_windows_client, windows_eddsa_public_key))
    
    # Linux laptop
    # UUID = C42157C2-9526-B07C-7E43-B4A9FC957957
    cursor.execute('''INSERT INTO vehicles (vehicle_id, update_readiness_status, update_install_status, update_id, vehicle_ip, vehicle_port, last_poll_time, aes_128, aes_256, ed25519_public_key)
                    VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?)''',
                    ('C42157C2-9526-B07C-7E43-B4A9FC957957', False, True, 2, linux_ip, linux_port, aes_128_linux_client, aes_256_linux_client, linux_eddsa_public_key))
    
    # Server UUID = 5B8DECB9-2A5B-48FA-966B-673B9A731C1F
    cursor.execute('''INSERT INTO network_information (local_ip, local_port, identifier)
                    VALUES (?, ?, ?)''',
                    (server_ip, server_port, '5B8DECB9-2A5B-48FA-966B-673B9A731C1F'))
    
    cursor.execute('''INSERT INTO cryptographic_data (ed25519_private_key, ed25519_public_key, server_private_key, server_certificate, root_ca)
                    VALUES (?, ?, ?, ?, ?)''',
                    (server_eddsa_private_key, server_eddsa_public_key, server_private_key, server_certificate, root_ca))
    
    # Example updates
    file_data, _ = get_update_file(file1)
    cursor.execute('''INSERT INTO updates (update_version, update_file)
                    VALUES (?, ?)''',
                    ('1.0.0.png', file_data))
    file_data, _ = get_update_file(file2)
    cursor.execute('''INSERT INTO updates (update_version, update_file)
                    VALUES (?, ?)''',
                    ('1.0.1.iso', file_data))
    file_data, _ = get_update_file(file3)
    cursor.execute('''INSERT INTO updates (update_version, update_file)
                    VALUES (?, ?)''',
                    ('1.0.2.w', file_data))
    file_data, _ = get_update_file(file4)
    cursor.execute('''INSERT INTO updates (update_version, update_file)
                    VALUES (?, ?)''',
                    ('1.0.3.png', file_data))
    file_data, _ = get_update_file(file6)
    cursor.execute('''INSERT INTO updates (update_version, update_file)
                    VALUES (?, ?)''',
                    ('1.0.5.jpg', file_data))
    
    print("Data added to the server database.")

    db_connection.commit()
    db_connection.close()
    print("Server database setup complete.")

    print("Setting up client Windows database ...")
    db_connection = sqlite3.connect("client_windows_ota_updates.db")
    cursor = db_connection.cursor()

    print("Creating tables ...")

    cursor.execute('''CREATE TABLE IF NOT EXISTS network_information (
                    network_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    server_ip TEXT,
                    server_port INTEGER,
                    local_ip TEXT,
                    local_port INTEGER,
                    identifier TEXT
                    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS update_information (
                    update_entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    update_version TEXT,
                    update_install_status BOOLEAN,
                    update_readiness_status BOOLEAN,
                    update_install_time TIMESTAMP
                    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS update_downloads (
                    download_entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    update_version TEXT,
                    update_file BLOB
                    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS cryptographic_data (
                    cryptographic_entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    aes_128 BLOB,
                    aes_256 BLOB,
                    ed25519_private_key BLOB,
                    ed25519_public_key BLOB,
                    server_ed25519_public_key BLOB,
                    windows_client_private_key BLOB,
                    windows_client_certificate BLOB,
                    root_ca BLOB
                    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS rollback_data (
                    rollback_entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    update_version TEXT,
                    update_file BLOB
                    )''')
    
    print("Tables created.")

    print("Adding data to the Windows client database ...")
    cursor.execute('''INSERT INTO network_information (server_ip, server_port, local_ip, local_port, identifier)
                    VALUES (?, ?, ?, ?, ?)''',
                    (server_ip, server_port, windows_ip, windows_port, 'CE41D0EA-C52B-E941-9F86-60F4FAF5CD8A'))
    
    file_data, _ = get_update_file(file3)
    cursor.execute('''INSERT INTO update_information (update_version, update_install_status, update_readiness_status, update_install_time)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)''',
                    ('1.0.2.w', True, False))
    
    cursor.execute('''INSERT INTO cryptographic_data (aes_128, aes_256, ed25519_private_key, ed25519_public_key, server_ed25519_public_key, windows_client_private_key, windows_client_certificate, root_ca)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                    (aes_128_windows_client, aes_256_windows_client, windows_eddsa_private_key, windows_eddsa_public_key, server_eddsa_public_key, windows_client_private_key, windows_client_certificate, root_ca))
    
    print("Data added to the Windows client database.")

    db_connection.commit()
    db_connection.close()
    print("Windows client database setup complete.")

    print("Setting up client Linux database ...")
    db_connection = sqlite3.connect("client_linux_ota_updates.db")
    cursor = db_connection.cursor()

    print("Creating tables ...")

    cursor.execute('''CREATE TABLE IF NOT EXISTS network_information (
                    network_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    server_ip TEXT,
                    server_port INTEGER,
                    local_ip TEXT,
                    local_port INTEGER,
                    identifier TEXT
                    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS update_information (
                    update_entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    update_version TEXT,
                    update_install_status BOOLEAN,
                    update_readiness_status BOOLEAN,
                    update_install_time TIMESTAMP
                    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS update_downloads (
                    download_entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    update_version TEXT,
                    update_file BLOB
                    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS cryptographic_data (
                    cryptographic_entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    aes_128 BLOB,
                    aes_256 BLOB,
                    ed25519_private_key BLOB,
                    ed25519_public_key BLOB,
                    server_ed25519_public_key BLOB,
                    linux_client_private_key BLOB,
                    linux_client_certificate BLOB,
                    root_ca BLOB
                    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS rollback_data (
                    rollback_entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    update_version TEXT,
                    update_file BLOB
                    )''')
    
    print("Tables created.")

    print("Adding data to the Linux database ...")
    cursor.execute('''INSERT INTO network_information (server_ip, server_port, local_ip, local_port, identifier)
                    VALUES (?, ?, ?, ?, ?)''',
                    (server_ip, server_port, linux_ip, linux_port, 'C42157C2-9526-B07C-7E43-B4A9FC957957'))
    
    file_data, _ = get_update_file(file4)
    cursor.execute('''INSERT INTO update_information (update_version, update_install_status, update_readiness_status, update_install_time)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)''',
                    ('1.0.3.png', True, False))
    
    cursor.execute('''INSERT INTO cryptographic_data (aes_128, aes_256, ed25519_private_key, ed25519_public_key, server_ed25519_public_key, linux_client_private_key, linux_client_certificate, root_ca)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                    (aes_128_linux_client, aes_256_linux_client, linux_eddsa_private_key, linux_eddsa_public_key, server_eddsa_public_key, linux_client_private_key, linux_client_certificate, root_ca))
    
    print("Data added to the Linux client database.")

    db_connection.commit()
    db_connection.close()
    print("Linux client database setup complete.")