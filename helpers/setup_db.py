import sqlite3

from constants import *

# Sets up the data base for the system
# Not dynamically created to simulate real application
# Uses SQLite for simplicity as database tehcnology is out of scope
if __name__=='__main__':
    db_connection = sqlite3.connect("ota_updates.db")
    cursor = db_connection.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS vehicles (
                    vehicle_id TEXT PRIMARY KEY,
                    update_readiness_status BOOLEAN,
                    update_id INTEGER REFERENCES updates(update_id),
                    vehicle_ip TEXT,
                    vehicle_port INTEGER,
                    server_ip TEXT,
                    server_port INTEGER,
                    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS updates (
                    update_id INTEGER PRIMARY KEY,
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
    # Example vehicle (management PC)
    cursor.execute('''INSERT INTO vehicles (vehicle_id, update_readiness_status, vehicle_ip, vehicle_port, server_ip, server_port)
                    VALUES (?, ?, ?, ?, ?, ?)''',
                    ('5B854E74-E19A-11E5-9C43-BC00007E0000', False, '192.168.225.200', 50200, '192.168.225.97', 50097))
    

    db_connection.commit()
    db_connection.close()