# HEADER FILE
# EXAMPLE

import ssl, platform, selectors, socket, time, random, types, os, errno, sqlite3, dotenv, typing
from constants import *
from functions import *
from server_functions import *

# Only the create connection part since the system should detect the use of invalid certificates and exit the connection
def connect_with_invalid_tls(selector: selectors.SelectSelector) -> typing.Tuple[selectors.SelectSelector, ssl.SSLSocket, int]:
    try:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT) # Auto-negotiates highgest available protocol
        context.minimum_version = ssl.TLSVersion.TLSv1_3 # Enforces NIST-approved TLS 1.3 ciphers
        context.verify_mode = ssl.CERT_REQUIRED
        
        # Change certs depending on if testing on local host or remote host
        os_type = platform.system()
        # Local host
        if os_type == "Windows":
            context.load_cert_chain(certfile="cryptographic_material\\server_malicious_root_ca_certificate_local_host.pem", keyfile="cryptographic_material\\server_malicious_root_ca_private_key_local_host.pem")
            context.load_verify_locations(cafile="cryptographic_material\\root_ca_malicious.pem")
        elif os_type == "Linux":
            context.load_cert_chain(certfile="cryptographic_material/server_malicious_root_ca_certificate_local_host.pem", keyfile="cryptographic_material/server_malicious_root_ca_private_key_local_host.pem")
            context.load_verify_locations(cafile="cryptographic_material/root_ca_malicious.pem")
        
        # Network
        # if os_type == "Windows":
        #     context.load_cert_chain(certfile="cryptographic_material\\server_malicious_root_ca_certificate_pi_client.pem", keyfile="cryptographic_material\\server_malicious_root_ca_private_key_pi_client.pem")
        #     context.load_verify_locations(cafile="cryptographic_material\\root_ca_malicious.pem")
        # elif os_type == "Linux":
        #     context.load_cert_chain(certfile="cryptographic_material/server_malicious_root_ca_certificate_pi_client.pem", keyfile="cryptographic_material/server_malicious_root_ca_private_key_pi_client.pem")
        #     context.load_verify_locations(cafile="cryptographic_material/root_ca_malicious.pem")

        connection_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connection_socket.setblocking(False)
        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        _, _, host, port, _ = get_client_network_information()
        data = types.SimpleNamespace(address=(host, port), inb=BYTES_NONE, outb=BYTES_NONE, connected=False, file_name=STR_NONE, data_subtype=INT_NONE, handshake_complete=False)
        
        # Waits for the connection to complete in a non-blocking way, but blocks all other operations
        connection_attempts = 0
        while not data.connected:
            err = connection_socket.connect_ex((host, port)) # Try connecting
            if err == 10056 or err == SUCCESS: # Connection made
                print(f"Connection to {host}:{port} successful.")
                data.connected = True
                break
            elif err == 10035 or err == errno.EINPROGRESS or err == errno.EALREADY: # Non-blocking connection in progress
                #print(f"Connection to {host}:{port} in progress ...")
                time.sleep(1)
                continue
            elif err == 10022 or err == errno.EINVAL: # Failed connction (no client at the address)
                #print("No device found at the specified address.")
                # Try up to 5 times to connect to the client
                if connection_attempts > 5:
                    #print("Connection attempts exceeded. Exiting ...")
                    return None, None, CONNECTION_INITIATE_ERROR
                #print("Trying again ...")
                time.sleep(5)
                connection_attempts += 1
                continue
            else:
                print(f"Connection to {host}:{port} failed with error: {errno.errorcode[err]}\n")
                print("Please check the host and port details.")
                return None, None, CONNECTION_INITIATE_ERROR

        # Wrap socket with TSL
        connection_socket = context.wrap_socket(connection_socket, do_handshake_on_connect=False, server_hostname=host) # Wraps the socket with TLS
        print("Initiating TLS handshake ...")
        start_time = time.time()
        while time.time() - start_time < 10:  # Wait 10 seconds until timing out
            try:
                connection_socket.do_handshake() # Can't measure the performance of this due to non-blocking nature
                # do_tls_handshake_stats = measure_operation(process, connection_socket.do_handshake)
                data.outb = HANDSHAKE_COMPLETE
                break
            except ssl.SSLWantReadError:
                # #print("SSLWantReadError during handshake.")
                continue
            except ssl.SSLWantWriteError:
                #print("SSLWantWriteError during handshake.")
                continue
            except ssl.SSLError as e:
                print(f"SSLError during handshake: {e}")
                return None, None, ERROR
            except Exception as e:
                print(f"An unexpected error occurred during handshake: {e}")
                return None, None, ERROR
        
        # Register the connection with the selector for read and write events
        selector.register(connection_socket, events, data=data)
        print("Socket registered.")

        print("Waiting for TLS handshake ...")
        ret_val = wait_for_TLS_handshake(connection_socket, selector)
        if ret_val != SUCCESS:
            print("Error during TLS handshake.")
            return None, None, ERROR
        #print("TLS handshake successful.")

        return selector, connection_socket, SUCCESS
    
    except Exception as e:
        print(f"An error occurred: {e}")
        _ = close_connection(connection_socket, selector)
        return None, None, CONNECTION_INITIATE_ERROR
    
# Fails authenticated encryption / fails decryption
# Only needs to send data not read it since client should except before processing data and a response
def use_invalid_encryption_key(selector: selectors.SelectSelector) -> int:
    try:        
        _, identifier, client_host, client_port, ret_val = get_client_network_information()
        if ret_val == ERROR:
            #print("An error occurred while retrieving the client network information.")
            return ERROR
        
        selector, connection_socket, ret_val = create_connection(client_host, client_port, selector)
        if ret_val == CONNECTION_INITIATE_ERROR:
            #print("Error: Connection initiation failed.")
            return CONNECTION_INITIATE_ERROR

        key = selector.get_key(connection_socket)

        key.data.identifier = identifier

        key.data.file_name, file_data, _ = get_update_file() # Use socket for global file name access
        key.data.data_subtype = UPDATE_FILE
        key.data.outb = file_data

        encryption_key = random.randbytes(16) # Use random invalid encryption key

        payload, ret_val = create_payload(key.data.outb, key.data.file_name, key.data.data_subtype, encryption_key)
        if ret_val == PAYLOAD_ENCRYPTION_ERROR:
            #print("Error: Failed to encrypt payload.")
            return PAYLOAD_ENCRYPTION_ERROR
        elif ret_val == PAYLOAD_CREATION_ERROR:
            #print("Error: Failed to create payload.")
            return PAYLOAD_CREATION_ERROR
        
        print("Payload created successfully with an invalid encryption key.")
        
        print(f"Sending data to {client_host}:{client_port}")
        while payload:
            sent = connection_socket.send(payload)
            payload = payload[sent:]
        key.data.outb = BYTES_NONE
        print("Data sent.")

        return SUCCESS

    except Exception as e:
        print(f"An error occurred: {e}")
        return ERROR
    
# Changes a single byte in the payload after the hash is generated to test the hash verification on the client-side
def use_invalid_hash(selector: selectors.SelectSelector) -> int:
    try:        
        _, identifier, client_host, client_port, ret_val = get_client_network_information()
        if ret_val == ERROR:
            #print("An error occurred while retrieving the client network information.")
            return ERROR
        
        selector, connection_socket, ret_val = create_connection(client_host, client_port, selector)
        if ret_val == CONNECTION_INITIATE_ERROR:
            #print("Error: Connection initiation failed.")
            return CONNECTION_INITIATE_ERROR

        key = selector.get_key(connection_socket)

        key.data.identifier = identifier

        key.data.file_name, file_data, _ = get_update_file() # Use socket for global file name access
        key.data.data_subtype = UPDATE_FILE
        key.data.outb = file_data

        dotenv.load_dotenv()
        database = os.getenv("SERVER_DATABASE") # No need use of a default database if SERVER_DATABASE is not found
        
        #print("Retrieving encryption key ...")
        encryption_key = BYTES_NONE
        db_connection = sqlite3.connect(database)
        cursor = db_connection.cursor()
        encryption_key = (cursor.execute(f"SELECT {ENCRYPTION_ALGORITHM} FROM vehicles WHERE vehicle_id = ?", (key.data.identifier,))).fetchone()[0]
        #print("Encryption key retrieved successfully.")
        db_connection.close()

        # Gets the senders identifier
        db_connection = sqlite3.connect(database)
        cursor = db_connection.cursor()
        identifier = (cursor.execute("SELECT identifier FROM network_information WHERE network_id = 1")).fetchone()[0]
        db_connection.close()

        # Determines if the data to be sent is just a status response or request, or it is actual data
        if key.data.outb in vars(constants).values() and not key.data.data_subtype: # Checks if the data to send is defined in the constants file
            key.data.data_type = STATUS_CODE
        else:
            key.data.data_type = DATA

        # Keeps the same header format even if endpoint is not sending a file
        if not key.data.file_name or type(key.data.file_name) == str:
            key.data.file_name = BYTES_NONE

        payload = key.data.file_name + key.data.outb

        # Security relating to update files, not response or request communications
        if key.data.data_subtype == UPDATE_FILE:
            #print("Generating hash ...")

            if HASHING_ALGORITHM == 'sha-256': # SHA-256
                #print("Using SHA-256 hashing algorithm.")
                update_file_hash = str.encode(hashlib.sha256(key.data.outb).hexdigest()) # Creates hash of the update file
            #print("Hash generated.")

            # Change update file by a single byte to test the hash verification
            key.data.outb += random.randbytes(1)
            payload = key.data.file_name + key.data.outb + update_file_hash

            db_connection = sqlite3.connect(database)
            cursor = db_connection.cursor()
            private_key = (cursor.execute(f"SELECT {SIGNATURE_ALGORITHM}_private_key FROM cryptographic_data WHERE cryptographic_entry_id = 1")).fetchone()[0]
            db_connection.close()

            payload, ret_val = generate_signature(payload, private_key)
            if ret_val == ERROR:
                #print("Error during signature generation.")
                return PAYLOAD_CREATION_ERROR
                    
        nonce, encrypted_payload, tag, ret_val = payload_encryption(payload, encryption_key)
        if ret_val != SUCCESS:
            #print("Error during payload encryption.")
            return PAYLOAD_ENCRYPTION_ERROR

        payload_length = len(encrypted_payload)

        # Only packs integers for the header
        header = struct.pack(PACK_DATA_COUNT, payload_length, key.data.data_type, len(key.data.file_name), key.data.data_subtype)

        payload = header + nonce + tag + str.encode(identifier) + encrypted_payload

        print("Payload created successfully with an invalid hash.")

        print(f"Sending data to {client_host}:{client_port}")
        while payload:
            sent = connection_socket.send(payload)
            payload = payload[sent:]
        key.data.outb = BYTES_NONE
        print("Data sent.")

        return SUCCESS

    except Exception as e:
        print(f"An error occurred: {e}")
        return ERROR
    
def use_invalid_signature(selector: selectors.SelectSelector) -> int:
    try:
        _, identifier, client_host, client_port, ret_val = get_client_network_information()
        if ret_val == ERROR:
            #print("An error occurred while retrieving the client network information.")
            return ERROR
        
        selector, connection_socket, ret_val = create_connection(client_host, client_port, selector)
        if ret_val == CONNECTION_INITIATE_ERROR:
            #print("Error: Connection initiation failed.")
            return CONNECTION_INITIATE_ERROR

        key = selector.get_key(connection_socket)

        key.data.identifier = identifier

        key.data.file_name, file_data, _ = get_update_file() # Use socket for global file name access
        key.data.data_subtype = UPDATE_FILE
        key.data.outb = file_data

        dotenv.load_dotenv()
        database = os.getenv("SERVER_DATABASE") # No need use of a default database if SERVER_DATABASE is not found
        
        #print("Retrieving encryption key ...")
        encryption_key = BYTES_NONE
        db_connection = sqlite3.connect(database)
        cursor = db_connection.cursor()
        encryption_key = (cursor.execute(f"SELECT {ENCRYPTION_ALGORITHM} FROM vehicles WHERE vehicle_id = ?", (key.data.identifier,))).fetchone()[0]
        #print("Encryption key retrieved successfully.")
        db_connection.close()

        # Gets the senders identifier
        db_connection = sqlite3.connect(database)
        cursor = db_connection.cursor()
        identifier = (cursor.execute("SELECT identifier FROM network_information WHERE network_id = 1")).fetchone()[0]
        db_connection.close()

        # Determines if the data to be sent is just a status response or request, or it is actual data
        if key.data.outb in vars(constants).values() and not key.data.data_subtype: # Checks if the data to send is defined in the constants file
            key.data.data_type = STATUS_CODE
        else:
            key.data.data_type = DATA

        # Keeps the same header format even if endpoint is not sending a file
        if not key.data.file_name or type(key.data.file_name) == str:
            key.data.file_name = BYTES_NONE

        payload = key.data.file_name + key.data.outb

        # Security relating to update files, not response or request communications
        if key.data.data_subtype == UPDATE_FILE:
            update_file_hash, ret_val = generate_hash(key.data.outb)
            if ret_val == ERROR:
                #print("Error during hash generation.")
                return PAYLOAD_CREATION_ERROR
            payload += update_file_hash

            # Generate a new Ed25519 private key to simulate signing data while trying to impersonate the original digital signature
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
            private_key = Ed25519PrivateKey.generate()
            private_key = private_key.private_bytes_raw()

            payload, ret_val = generate_signature(payload, private_key)
            if ret_val == ERROR:
                #print("Error during signature generation.")
                return PAYLOAD_CREATION_ERROR
                    
        nonce, encrypted_payload, tag, ret_val = payload_encryption(payload, encryption_key)
        if ret_val != SUCCESS:
            #print("Error during payload encryption.")
            return PAYLOAD_ENCRYPTION_ERROR

        payload_length = len(encrypted_payload)

        # Only packs integers for the header
        header = struct.pack(PACK_DATA_COUNT, payload_length, key.data.data_type, len(key.data.file_name), key.data.data_subtype)

        payload = header + nonce + tag + str.encode(identifier) + encrypted_payload

        print("Payload created successfully with an invalid signature.")

        print(f"Sending data to {client_host}:{client_port}")
        while payload:
            sent = connection_socket.send(payload)
            payload = payload[sent:]
        key.data.outb = BYTES_NONE
        print("Data sent.")

        return SUCCESS

    except Exception as e:
        print(f"An error occurred: {e}")
        return ERROR