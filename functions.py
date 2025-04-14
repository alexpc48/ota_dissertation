# HEADER FILE
# Common functions for both the server and client

# Libraries
import socket
import sqlite3
import selectors
import struct
import types
import errno
import time
import constants

from constants import *
from cryptographic_functions import *

# Closes connection with the socket and selector specified
def close_connection(connection_socket: socket.socket, selector: selectors.SelectSelector) -> int:
    try:
        try:
            selector.get_key(connection_socket)  # This will raise KeyError if not registered
            selector.unregister(connection_socket)
            print("Socket unregistered from selector.")
        except KeyError:
            print("Socket is not registered with selector.")

        if connection_socket.fileno() != -1:
            connection_socket.close()
            print("Socket closed.")
        else:
            print("Socket is not open")

        return SUCCESS

    except Exception as e:
        print(f"An error occurred: {e}")
        return ERROR
    
# Global variable to store the listening socket information
# Constatnt for duration of execution
# Used for determining what database to use
LISTENING_SOCKET_INFO = None
# Creates a listening socket and registers it with the selector
def create_listening_socket(host: str, port: int, selector: selectors.SelectSelector) -> int:
    global LISTENING_SOCKET_INFO
    try:
        print(f"Creating listening socket on {host}:{port} ...")
        listening_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listening_socket.bind((host, port))
        listening_socket.listen()
        listening_socket.setblocking(False)

        LISTENING_SOCKET_INFO = listening_socket.getsockname()

        # Register the listening socket with the selector
        selector.register(listening_socket, selectors.EVENT_READ, data="listening_socket")
        print(f"Listening on {host}:{port} for connections ...")
        return SUCCESS
    
    except Exception as e:
        print(f"An error occurred: {e}")
        _ = close_connection(listening_socket, selector)
        return LISTENING_SOCKET_CREATION_ERROR
    
# Accepts new connections
# TODO: Only accept registerd connection endpoints
def accept_new_connection(socket: socket.socket, selector: selectors.SelectSelector) -> int:
    try:
        print("Accepting new connection ...")

        # TLS implementation
        import ssl
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER) # Auto-negotiates highgest available protocol
        context.options |= ssl.OP_NO_SSLv2
        context.options |= ssl.OP_NO_SSLv3
        context.options |= ssl.OP_NO_TLSv1
        context.options |= ssl.OP_NO_TLSv1_1
        context.set_ciphers("HIGH:!aNULL:!eNULL:!MD5:!3DES")
        connection_certificate = "server_certificate.pem"
        connection_private_key = "server_private_key.pem"
        context.load_cert_chain(certfile=connection_certificate, keyfile=connection_private_key)
        root_ca = "root_ca.pem"
        context.load_verify_locations(cafile=root_ca)
        context.verify_mode = ssl.CERT_REQUIRED
        context.check_hostname = False # No hostnames in use, but real implementation would
        context.set_debug_level(1)

        connection_socket, address = socket.accept()
        print(f"Accepted connection from {address[0]}:{address[1]} ...")
        connection_socket.setblocking(False)

        # TLS implementation
        connection_socket = context.wrap_socket(connection_socket, server_side=True, do_handshake_on_connect=False)

        # Register the connection with the selector
        data = types.SimpleNamespace(address=address, inb=BYTES_NONE, outb=BYTES_NONE, file_name=STR_NONE, data_subtype=INT_NONE)
        events = selectors.EVENT_READ | selectors.EVENT_WRITE # Allow socket to read and write
        selector.register(connection_socket, events, data=data)
        print(f"Connection from {address[0]}:{address[1]} registered with the selector.")
        # print("[ACK]")
        return SUCCESS
    
    except Exception as e:
        print(f"An error occurred: {e}")
        _ = close_connection(connection_socket, selector)
        return CONNECTION_ACCEPT_ERROR
    
# Creates a connection to an endpoint
# TODO: Only connect to registered endpoints
def create_connection(host: str, port: int, selector: selectors.SelectSelector) -> typing.Tuple[selectors.SelectSelector, socket.socket, int]:
    try:
        print(f"Initiating connection to {host}:{port} ...")

       
        connection_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connection_socket.setblocking(False)

        # TLS implementation
        import ssl
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT) # Auto-negotiates highgest available protocol
        context.options |= ssl.OP_NO_SSLv2
        context.options |= ssl.OP_NO_SSLv3
        context.options |= ssl.OP_NO_TLSv1
        context.options |= ssl.OP_NO_TLSv1_1
        context.set_ciphers("HIGH:!aNULL:!eNULL:!MD5:!3DES")
        connection_certificate = "client_certificate.pem"
        connection_private_key = "client_private_key.pem"
        context.load_cert_chain(certfile=connection_certificate, keyfile=connection_private_key)
        root_ca = "root_ca.pem"
        context.load_verify_locations(cafile=root_ca)
        context.verify_mode = ssl.CERT_REQUIRED
        context.check_hostname = False
        context.set_debug_level(1)

        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        data = types.SimpleNamespace(address=(host, port), inb=BYTES_NONE, outb=BYTES_NONE, connected=False, file_name=STR_NONE, data_subtype=INT_NONE)
        
        # Waits for the connection to complete in a non-blocking way, but blocks all other operations
        connection_attempts = 0
        timeout_interval = random.randint(1, 10)
        time.sleep(timeout_interval) # Refreshes in random intervals to avoid connection collisions
        while not data.connected:
            err = connection_socket.connect_ex((host, port)) # Try connecting
            # print("[SYN]")
            if err == 10056 or err == SUCCESS: # Connection made
                print(f"Connection to {host}:{port} successful.")
                data.connected = True
                # print("[SYN-ACK]")
                break
            elif err == 10035 or err == errno.EINPROGRESS or err == errno.EALREADY: # Non-blocking connection in progress
                print(f"Connection to {host}:{port} in progress ...")
                time.sleep(1)
                continue
            elif err == 10022 or err == errno.EINVAL: # Failed connction (no client at the address)
                print("No device found at the specified address.")
                # Try up to 5 times to connect to the client
                if connection_attempts > 5:
                    print("Connection attempts exceeded. Exiting ...")
                    return None, None, CONNECTION_INITIATE_ERROR
                print("Trying again ...")
                time.sleep(5)
                connection_attempts += 1
                continue
            else:
                print(f"Connection to {host}:{port} failed with error: {errno.errorcode[err]}\n")
                print("Please check the host and port details.")
                return None, None, CONNECTION_INITIATE_ERROR

        # TLS implementation
        connection_socket = context.wrap_socket(connection_socket, do_handshake_on_connect=False) # Wraps the socket with TLS
        while True:
            try:
                print("Performing TLS handshake ...")
                connection_socket.do_handshake()
                print("TLS handshake successful.")
                break
            except ssl.SSLWantReadError:
                # print("SSLWantReadError during handshake.")
                continue
            except ssl.SSLWantWriteError:
                print("SSLWantWriteError during handshake.")
            except ssl.SSLError as e:
                print(f"SSLError during handshake: {e}")
                return False
            except Exception as e:
                print(f"An unexpected error occurred during handshake: {e}")
                return False
        # Register the connection with the selector for read and write events
        selector.register(connection_socket, events, data=data)
        print("Socket registered.")

        return selector, connection_socket, SUCCESS
    
    except Exception as e:
        print(f"An error occurred: {e}")
        _ = close_connection(connection_socket, selector)
        return None, None, CONNECTION_INITIATE_ERROR

# Receives the payload from the socket
def receive_payload(connection_socket: socket.socket) -> typing.Tuple[bytes, bytes, int, int, str, int]:
    try:
        file_name = BYTES_NONE # Initialise variable

        # Read the packet header
        # Receive packed data (integers)
        print("Receiving header ...")
        header = connection_socket.recv(PACK_COUNT_BYTES) # Receives the amount of bytes in the struct.pack header
        if header == BYTES_NONE: # Closes connection if no data is received from the remote connection
            print("No data received.")
            return BYTES_NONE, BYTES_NONE, INT_NONE, INT_NONE, STR_NONE, CONNECTION_CLOSE_ERROR
        print("Header received.")

        # Continue if data is received
        # Data arrives as header -> nonce -> tag -> identifier -> payload
        # Identifier not sensitive - in application could be the VIN of the vehicle
        if header:
            # Receive the nonce and tag
            print("Receiving nonce ...")
            nonce = connection_socket.recv(NONCE_LENGTH)
            print(f"Nonce: {nonce}")
            print("Receiving tag ...")
            tag = connection_socket.recv(TAG_LENGTH)
            print(f"Tag: {tag}")

            print("Receiving identifier ...")
            identifier = (connection_socket.recv(IDENTIFIER_LENGTH)).decode()
            print(f"Identifier: {identifier}")

            # Uses listening port to determine which database to use
            # Formatted queries acceptable since variables are not user input
            # Potential for risk identifier is captured and replayed as SQL injection attack
            _, port = LISTENING_SOCKET_INFO
            dotenv.load_dotenv()
            if port == SERVER_PORT:
                database = os.getenv("SERVER_DATABASE")
                encryption_query = f"SELECT {ENCRYPTION_ALGORITHM} FROM vehicles WHERE vehicle_id = ? LIMIT 1" # (identifier,)
                sign_query = f"SELECT {SIGNATURE_ALGORITHM}_public_key FROM vehicles WHERE vehicle_id = ? LIMIT 1" # (identifier,)
            elif port == WINDOWS_PORT:
                database = os.getenv("WINDOWS_CLIENT_DATABASE")
                encryption_query = f"SELECT {ENCRYPTION_ALGORITHM} FROM cryptographic_data LIMIT 1"
                sign_query = f"SELECT server_{SIGNATURE_ALGORITHM}_public_key FROM cryptographic_data LIMIT 1"
            elif port == LINUX_PORT:
                database = os.getenv("LINUX_CLIENT_DATABASE")
                encryption_query = f"SELECT {ENCRYPTION_ALGORITHM} FROM cryptographic_data LIMIT 1"
                sign_query = f"SELECT server_{SIGNATURE_ALGORITHM}_public_key FROM cryptographic_data LIMIT 1"

            # Retrieve symmetric encrypion key
            print(f"Retrieving encryption key from {database} ...")
            db_connection = sqlite3.connect(database)
            cursor = db_connection.cursor()
            if port == SERVER_PORT:
                encryption_key = (cursor.execute(encryption_query, (identifier,))).fetchone()[0]
            else:
                encryption_key = (cursor.execute(encryption_query)).fetchone()[0]
            db_connection.close()
            print("Retrieved encryption key.")
                    
            # Unpack the header
            print("Unpacking header ...")
            payload_length, data_type, file_name_length, data_subtype = struct.unpack(PACK_DATA_COUNT, header[:PACK_COUNT_BYTES])
            print("Header unpacked.")

            print("Receiving payload ...")
            payload = BYTES_NONE # Initialise variable
            while len(payload) < payload_length:
                try:
                    chunk = connection_socket.recv(BYTES_TO_READ) # TODO: Check resource usage and compare between receiving all bytes at once or if splitting it up into 1024 is better for an embedded system
                except BlockingIOError as e:
                    print(f"BlockingIOError: {e}")
                    if e.errno == errno.EAGAIN:
                        print("Resource temporarily unavailable. Retrying ...")
                        time.sleep(1) # Wait for a second before retrying
                        continue
                if not chunk:
                    print("Connection closed before receiving the full payload.")
                    return BYTES_NONE, BYTES_NONE, INT_NONE, INT_NONE, STR_NONE, INCOMPLETE_PAYLOAD_ERROR
                payload += chunk
            print("Payload received.")
            
            payload, ret_val = payload_decryption(payload, nonce, tag, encryption_key) # Decrypt the payload
            if ret_val != SUCCESS:
                print("Error during payload decryption.")
                return BYTES_NONE, BYTES_NONE, INT_NONE, INT_NONE, STR_NONE, PAYLOAD_DECRYPTION_ERROR
            
            file_name = payload[:file_name_length]
            print(f"File name: {file_name}")

            # Verify the hash and signature of an update file only
            if data_subtype == UPDATE_FILE:                
                data_inb, ret_val = verify_hash(payload, file_name_length, payload_length)
                if ret_val == SUCCESS:
                    print("Hash is valid.")
                elif INVALID_PAYLOAD_ERROR:
                    print("Hash is invalid.")
                    return BYTES_NONE, BYTES_NONE, INT_NONE, INT_NONE, STR_NONE, PAYLOAD_RECEIVE_ERROR
                else:
                    print("Error during hash verification.")
                    return BYTES_NONE, BYTES_NONE, INT_NONE, INT_NONE, STR_NONE, PAYLOAD_RECEIVE_ERROR

                # Retrieve the signature public key from the database
                # Server filters to the clients ID
                # Clients only have the servers public key so no need to filter
                # print(f"Retrieving signature public key from {database} ...")
                db_connection = sqlite3.connect(database)
                cursor = db_connection.cursor()
                if port == SERVER_PORT:
                    public_key = (cursor.execute(sign_query, (identifier,))).fetchone()[0]
                else:
                    public_key = (cursor.execute(sign_query)).fetchone()[0]
                db_connection.close()
                # print("Retrieved signature public key.")

                ret_val = verify_signature(public_key, payload, payload_length)
                if ret_val == SUCCESS:
                    print("Signature is valid.")
                elif SIGNATURE_INVALID_ERROR:
                    print("Signature is invalid.")
                    return BYTES_NONE, BYTES_NONE, INT_NONE, INT_NONE, STR_NONE, PAYLOAD_RECEIVE_ERROR
                else:
                    print("Error during signature verification.")
                    return BYTES_NONE, BYTES_NONE, INT_NONE, INT_NONE, STR_NONE, PAYLOAD_RECEIVE_ERROR

            # If the payload is not an update file, just extract the data     
            else:
                data_inb = payload[file_name_length:payload_length]
                # print(f"Payload: {data_inb}")

            return file_name, data_inb, data_type, data_subtype, identifier, SUCCESS

    except Exception as e:
        print(f"An error occurred: {e}")
        return BYTES_NONE, BYTES_NONE, INT_NONE, INT_NONE, STR_NONE, PAYLOAD_RECEIVE_ERROR

def create_payload(data_to_send: bytes, file_name: bytes, data_subtype: int, encryption_key: bytes) -> typing.Tuple[bytes, int]:
    try:
        # Query for getting relevant database
        dotenv.load_dotenv()
        _, port = LISTENING_SOCKET_INFO
        if port == SERVER_PORT:
            database = os.getenv("SERVER_DATABASE")
        elif port == WINDOWS_PORT:
            database = os.getenv("WINDOWS_CLIENT_DATABASE")
        elif port == LINUX_PORT:
            database = os.getenv("LINUX_CLIENT_DATABASE")

        # Gets the endpoints identifier
        db_connection = sqlite3.connect(database)
        cursor = db_connection.cursor()
        identifier = (cursor.execute("SELECT identifier FROM network_information WHERE network_id = 1")).fetchone()[0]
        db_connection.close()

        # Determines if the data to be sent is just a status response or request, or it is actual data
        if data_to_send in vars(constants).values(): # Checks if the data to send is defined in the constants file
            data_type = STATUS_CODE
        else:
            data_type = DATA

        # Keeps the same header format even if endpoint is not sending a file
        if not file_name or type(file_name) == str:
            file_name = BYTES_NONE

        payload = file_name + data_to_send

        # Security relating to update files, not response or request communications
        if data_subtype == UPDATE_FILE:
            update_file = data_to_send
            update_file_hash, ret_val = generate_hash(update_file)
            if ret_val == ERROR:
                print("Error during hash generation.")
                return BYTES_NONE, PAYLOAD_CREATION_ERROR
            payload += update_file_hash

            db_connection = sqlite3.connect(database)
            cursor = db_connection.cursor()
            private_key = (cursor.execute(f"SELECT {SIGNATURE_ALGORITHM}_private_key FROM cryptographic_data WHERE cryptographic_entry_id = 1")).fetchone()[0]
            db_connection.close()

            payload, ret_val = generate_signature(payload, private_key)
            if ret_val == ERROR:
                print("Error during signature generation.")
                return BYTES_NONE, PAYLOAD_CREATION_ERROR
                    
        nonce, encrypted_payload, tag, ret_val = payload_encryption(payload, encryption_key)
        if ret_val != SUCCESS:
            print("Error during payload encryption.")
            return BYTES_NONE, PAYLOAD_ENCRYPTION_ERROR

        payload_length = len(encrypted_payload)

        # Only packs integers for the header
        header = struct.pack(PACK_DATA_COUNT, payload_length, data_type, len(file_name), data_subtype)

        data_to_send = header + nonce + tag + str.encode(identifier) + encrypted_payload

        return data_to_send, SUCCESS

    except Exception as e:
        print(f"An error occurred: {e}")
        return BYTES_NONE, PAYLOAD_CREATION_ERROR