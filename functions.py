# HEADER FILE
# Common functions for both the server and client

# Libraries
import socket
import sqlite3
import selectors
import struct
import types
import errno
import tracemalloc
import time
import ssl
import constants
import datetime
import psutil
import os
import dotenv

from constants import *
from cryptographic_functions import *

# Closes connection with the socket and selector specified
def close_connection(connection_socket: ssl.SSLSocket, selector: selectors.SelectSelector) -> int:
    try:
        try:
            selector.get_key(connection_socket)  # This will raise KeyError if not registered
            selector.unregister(connection_socket)
            print("Socket unregistered from selector.")
        except KeyError:
            print("Socket is not registered with selector.")

        if connection_socket.fileno() != -1:
            # Waits until client sends its close_notify
            tls_unwrap = False
            start_time = time.time()
            while time.time() - start_time < 10:  # Wait 10 seconds until timing out
                try:
                    print("Unwrapping TLS ...")
                    connection_socket = connection_socket.unwrap() # Removes TLS
                    tls_unwrap = True
                    print("TLS unwrapped.")
                    break
                except ssl.SSLWantReadError:
                    continue
                except ssl.SSLWantWriteError:
                    continue
                except Exception as e:
                    print(f"An error occurred during socket unwrap: {e}")
                    break
            if tls_unwrap == False:
                print("TLS unwrap timed out.")
                print("Abruptly closing socket ...")
            else:
                print("Closing socket ...")
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
def accept_new_connection(socket: socket.socket, selector: selectors.SelectSelector) -> int:
    try:
        print("Accepting new connection ...")

        # TLS implementation
        context, _ = create_context('server')
        _, port = LISTENING_SOCKET_INFO
        if port == SERVER_PORT:
            database = os.getenv("SERVER_DATABASE")
            query = "SELECT server_private_key, server_certificate, root_ca FROM cryptographic_data WHERE cryptographic_entry_id = 1"
        elif port == WINDOWS_PORT:
            database = os.getenv("WINDOWS_CLIENT_DATABASE")
            query = "SELECT windows_client_private_key, windows_client_certificate, root_ca FROM cryptographic_data WHERE cryptographic_entry_id = 1"
        elif port == LINUX_PORT:
            database = os.getenv("LINUX_CLIENT_DATABASE")
            query = "SELECT linux_client_private_key, linux_client_certificate, root_ca FROM cryptographic_data WHERE cryptographic_entry_id = 1"

        db_connection = sqlite3.connect(database)
        cursor = db_connection.cursor()
        connection_private_key, connection_certificate, root_ca = (cursor.execute(query)).fetchone()
        connection_private_key = connection_private_key.decode()
        connection_certificate = connection_certificate.decode()
        root_ca = root_ca.decode()
        db_connection.close()

        connection_private_key_file = "accept_connection_private_key.pem"
        connection_certificate_file = "accept_connection_certificate.pem"
        root_ca_file = "root_ca.pem"

        # Work around for having hardcoded certificate paths
        # Allows server and clients to use their certificates
        with open(connection_private_key_file, "w", newline='') as connection_private_key_temp, open(connection_certificate_file, "w", newline='') as connection_certificate_temp, open(root_ca_file, "w", newline='') as root_ca_temp:
            connection_private_key_temp.write(connection_private_key)
            connection_certificate_temp.write(connection_certificate)
            root_ca_temp.write(root_ca)
        context.load_cert_chain(certfile=connection_certificate_file, keyfile=connection_private_key_file)
        context.load_verify_locations(cafile="root_ca.pem")
        print("Certificates loaded.")
        print("Removing temporary files ...")
        try:
            os.remove(connection_private_key_file)
            os.remove(connection_certificate_file)
            os.remove(root_ca_file)
        except:
            print("1 or more temporary files not found.")
        print("Temporary files removed.")

        connection_socket, address = socket.accept()
        print(f"Accepted connection from {address[0]}:{address[1]} ...")
        connection_socket.setblocking(False)

        # Wrap the socket with TLS
        connection_socket = context.wrap_socket(connection_socket, server_side=True, do_handshake_on_connect=False)

        # Register the connection with the selector
        data = types.SimpleNamespace(address=address, inb=BYTES_NONE, outb=BYTES_NONE, file_name=STR_NONE, data_subtype=INT_NONE, handshake_complete=False)
        events = selectors.EVENT_READ | selectors.EVENT_WRITE # Allow socket to read and write
        selector.register(connection_socket, events, data=data)
        print(f"Connection from {address[0]}:{address[1]} registered with the selector.")

        print("Waiting for TLS handshake ...")
        # Waits for TLS handshake confirmation to be sent
        start_time = time.time()
        while time.time() - start_time < 10:  # Wait 10 seconds until timing out
            # Get list of events from the selector
            timeout_interval = random.randint(1, 10)
            events = selector.select(timeout=timeout_interval)
            for key, mask in events:
                if key.data == "listening_socket":
                    continue

                connection_socket = key.fileobj

                if data.outb != HANDSHAKE_COMPLETE:
                    # Read events
                    if mask & selectors.EVENT_READ:                        
                        try:
                            data.inb = connection_socket.recv(STATUS_CODE_SIZE)
                            if data.inb == HANDSHAKE_COMPLETE:
                                print("TLS handshake complete.")
                                data.outb = HANDSHAKE_FINISHED
                            data.handshake_complete = True
                        except ssl.SSLWantReadError:
                            continue
                        except ssl.SSLWantWriteError:
                            continue
                if mask & selectors.EVENT_WRITE:
                    if data.outb:
                        while data.outb:
                            sent = connection_socket.send(data.outb)
                            data.outb = data.outb[sent:]
                        data.outb = BYTES_NONE
                        print("Data sent.")
                        break

            if data.handshake_complete == True:
                data.inb = BYTES_NONE
                data.outb = BYTES_NONE
                break
        if data.handshake_complete == False:
            print("TLS handshake timed out.")
            return ERROR
        print("TLS handshake successful.")
        return SUCCESS
    
    except Exception as e:
        print(f"An error occurred: {e}")
        _ = close_connection(connection_socket, selector)
        return CONNECTION_ACCEPT_ERROR
    
# Creates a connection to an endpoint
def create_connection(host: str, port: int, selector: selectors.SelectSelector) -> typing.Tuple[selectors.SelectSelector, ssl.SSLSocket, int]:
    try:
        # TLS implementation
        context, _ = create_context('client')
        _, check_port = LISTENING_SOCKET_INFO
        if check_port == SERVER_PORT:
            database = os.getenv("SERVER_DATABASE")
            query = "SELECT server_private_key, server_certificate, root_ca FROM cryptographic_data WHERE cryptographic_entry_id = 1"
        elif check_port == WINDOWS_PORT:
            database = os.getenv("WINDOWS_CLIENT_DATABASE")
            query = "SELECT windows_client_private_key, windows_client_certificate, root_ca FROM cryptographic_data WHERE cryptographic_entry_id = 1"
        elif check_port == LINUX_PORT:
            database = os.getenv("LINUX_CLIENT_DATABASE")
            query = "SELECT linux_client_private_key, linux_client_certificate, root_ca FROM cryptographic_data WHERE cryptographic_entry_id = 1"

        db_connection = sqlite3.connect(database)
        cursor = db_connection.cursor()
        connection_private_key, connection_certificate, root_ca = (cursor.execute(query)).fetchone()
        connection_private_key = connection_private_key.decode()
        connection_certificate = connection_certificate.decode()
        root_ca = root_ca.decode()
        db_connection.close()

        connection_private_key_file = "create_connection_private_key.pem"
        connection_certificate_file = "create_connection_certificate.pem"
        root_ca_file = "root_ca.pem"

        # Work around for having hardcoded certificate paths
        # Allows server and clients to use their certificates
        with open(connection_private_key_file, "w", newline='') as connection_private_key_temp, open(connection_certificate_file, "w", newline='') as connection_certificate_temp, open(root_ca_file, "w", newline='') as root_ca_temp:
            connection_private_key_temp.write(connection_private_key)
            connection_certificate_temp.write(connection_certificate)
            root_ca_temp.write(root_ca)
        context.load_cert_chain(certfile=connection_certificate_file, keyfile=connection_private_key_file)
        context.load_verify_locations(cafile="root_ca.pem")
        print("Certificates loaded.")
        print("Removing temporary files ...")
        try:
            os.remove(connection_private_key_file)
            os.remove(connection_certificate_file)
            os.remove(root_ca_file)
        except:
            print("1 or more temporary files not found.")
        print("Temporary files removed.")

        print(f"Initiating connection to {host}:{port} ...")

        connection_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connection_socket.setblocking(False)

        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        data = types.SimpleNamespace(address=(host, port), inb=BYTES_NONE, outb=BYTES_NONE, connected=False, file_name=STR_NONE, data_subtype=INT_NONE, handshake_complete=False)
        
        # Waits for the connection to complete in a non-blocking way, but blocks all other operations
        connection_attempts = 0
        timeout_interval = random.randint(1, 10)
        time.sleep(timeout_interval) # Refreshes in random intervals to avoid connection collisions
        while not data.connected:
            err = connection_socket.connect_ex((host, port)) # Try connecting
            if err == 10056 or err == SUCCESS: # Connection made
                print(f"Connection to {host}:{port} successful.")
                data.connected = True
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
        start_time = time.time()
        while time.time() - start_time < 10:  # Wait 10 seconds until timing out
            try:
                # print("Performing TLS handshake ...")
                connection_socket.do_handshake()
                data.outb = HANDSHAKE_COMPLETE
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

        print("Waiting for TLS handshake ...")
        # Waits for TLS handshake confirmation to be sent
        while True:
            # Get list of events from the selector
            timeout_interval = random.randint(1, 10)
            events = selector.select(timeout=timeout_interval)
            for key, mask in events:
                if key.data == "listening_socket":
                    continue

                connection_socket = key.fileobj

                if data.outb != HANDSHAKE_COMPLETE:
                    # Read events
                    if mask & selectors.EVENT_READ:                        
                        try:
                            data.inb = connection_socket.recv(STATUS_CODE_SIZE)
                            if data.inb == HANDSHAKE_COMPLETE:
                                print("TLS handshake complete.")
                                data.outb = HANDSHAKE_FINISHED
                            data.handshake_complete = True
                        except ssl.SSLWantReadError:
                            continue
                        except ssl.SSLWantWriteError:
                            continue
                if mask & selectors.EVENT_WRITE:
                    if data.outb:
                        while data.outb:
                            sent = connection_socket.send(data.outb)
                            data.outb = data.outb[sent:]
                        data.outb = BYTES_NONE
                        print("Data sent.")
                        break

            if data.handshake_complete == True:
                data.inb = BYTES_NONE
                data.outb = BYTES_NONE
                break
        if data.handshake_complete == False:
            print("TLS handshake timed out.")
            return ERROR
        print("TLS handshake successful.")
        return selector, connection_socket, SUCCESS
    
    except Exception as e:
        print(f"An error occurred: {e}")
        _ = close_connection(connection_socket, selector)
        return None, None, CONNECTION_INITIATE_ERROR

# Wrapper for receiving data from the socket
def connection_receive(connection_socket: socket.socket, bytes_to_read: int) -> typing.Tuple[bytes, int]:
    start_time = time.time()
    while time.time() - start_time < 10:  # Wait 10 seconds until timing out
        try:
            received_bytes = connection_socket.recv(bytes_to_read)
            return received_bytes, SUCCESS
        
        except ssl.SSLWantReadError:
            # print("SSLWantReadError: Waiting for more data to be readable...")
            continue
    
        except ssl.SSLWantWriteError:
            # print("SSLWantWriteError: Waiting until socket is writable...")
            continue
    print("Timeout: No data received within 10 seconds.")
    return BYTES_NONE, TIMEOUT_ERROR

# ChatGPT used to help create a metrics capture for security operations
def measure_operation(process, func, *args, **kwargs):
    """Profile a specific function call and return result + diagnostics."""
    tracemalloc.start()
    snapshot_start = tracemalloc.take_snapshot()

    cpu_times_start = process.cpu_times()
    _ = process.cpu_percent(interval=None)
    mem_info_start = process.memory_full_info()

    start_time = time.perf_counter()
    result = func(*args, **kwargs)
    elapsed_time = time.perf_counter() - start_time

    cpu_times_end = process.cpu_times()
    mem_info_end = process.memory_full_info()
    cpu_percent = process.cpu_percent(interval=None)
    snapshot_end = tracemalloc.take_snapshot()
    
    # CPU and memory metrics
    cpu_user = cpu_times_end.user - cpu_times_start.user
    cpu_sys = cpu_times_end.system - cpu_times_start.system
    cpu_total = cpu_user + cpu_sys
    mem_rss = mem_info_end.rss - mem_info_start.rss
    mem_uss = getattr(mem_info_end, 'uss', 0) - getattr(mem_info_start, 'uss', 0)
    cpu_equiv = cpu_total / elapsed_time if elapsed_time > 0 else 0

    py_alloc = sum(stat.size_diff for stat in snapshot_end.compare_to(snapshot_start, 'lineno'))
    tracemalloc.stop()

    return result, {
        "time": elapsed_time,
        "cpu_user": cpu_user,
        "cpu_sys": cpu_sys,
        "cpu_total": cpu_total,
        "cpu_percent": cpu_percent,
        "cpu_equiv": cpu_equiv,
        "mem_rss": mem_rss,
        "mem_uss": mem_uss,
        "py_mem": py_alloc
    }

def log_section(name, stats, f):
    if not stats: return
    f.write(f"{name}:\n")
    f.write(f"  Time:                        {stats['time']:.9f} sec\n")
    f.write(f"  CPU time (user):             {stats['cpu_user']:.9f} sec\n")
    f.write(f"  CPU time (system):           {stats['cpu_sys']:.9f} sec\n")
    f.write(f"  Total CPU time:              {stats['cpu_total']:.9f} sec\n")
    f.write(f"  Effective CPU cores used:    {stats['cpu_equiv']:.2f}x\n")
    f.write(f"  CPU usage during operation:  ~{stats['cpu_percent']:.2f}%\n")
    f.write(f"  Memory change (RSS):         {stats['mem_rss']} bytes\n")
    f.write(f"  Memory change (USS):         {stats['mem_uss']} bytes\n")
    f.write(f"  Python memory allocated:     {stats['py_mem']} bytes\n\n")

# Receives the payload from the socket
def receive_payload(connection_socket: ssl.SSLSocket) -> typing.Tuple[bytes, bytes, int, int, str, int]:
    try:
        file_name = BYTES_NONE # Initialise variable

        # Read the packet header
        # Receive packed data (integers)
        header, ret_val = connection_receive(connection_socket, PACK_COUNT_BYTES) # Receives the amount of bytes in the struct.pack header
        if ret_val != SUCCESS:
            print("Error during connection receive.")
            return BYTES_NONE, BYTES_NONE, INT_NONE, INT_NONE, STR_NONE, PAYLOAD_RECEIVE_ERROR
        if header == BYTES_NONE: # Closes connection if no data is received from the remote connection
            print("No data received.")
            return BYTES_NONE, BYTES_NONE, INT_NONE, INT_NONE, STR_NONE, CONNECTION_CLOSE_ERROR
        print("Header received.")
        print(f"Header: {header}")

        # Continue if data is received
        # Data arrives as header -> nonce -> tag -> identifier -> payload
        # Identifier not sensitive - in application could be the VIN of the vehicle
        if header:
            # Receive the nonce and tag
            print("Receiving nonce ...")
            nonce, ret_val = connection_receive(connection_socket, NONCE_LENGTH)
            if ret_val != SUCCESS:
                print("Error during connection receive.")
                return BYTES_NONE, BYTES_NONE, INT_NONE, INT_NONE, STR_NONE, PAYLOAD_RECEIVE_ERROR
            print(f"Nonce: {nonce}")
            print("Receiving tag ...")
            tag, ret_val = connection_receive(connection_socket, TAG_LENGTH)
            if ret_val != SUCCESS:
                print("Error during connection receive.")
                return BYTES_NONE, BYTES_NONE, INT_NONE, INT_NONE, STR_NONE, PAYLOAD_RECEIVE_ERROR
            print(f"Tag: {tag}")

            print("Receiving identifier ...")
            identifier, ret_val = connection_receive(connection_socket, IDENTIFIER_LENGTH)
            if ret_val != SUCCESS:
                print("Error during connection receive.")
                return BYTES_NONE, BYTES_NONE, INT_NONE, INT_NONE, STR_NONE, PAYLOAD_RECEIVE_ERROR
            identifier = identifier.decode()
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
                diagnostics_file = "server_diagnostics.txt"
            elif port == WINDOWS_PORT:
                database = os.getenv("WINDOWS_CLIENT_DATABASE")
                encryption_query = f"SELECT {ENCRYPTION_ALGORITHM} FROM cryptographic_data LIMIT 1"
                sign_query = f"SELECT server_{SIGNATURE_ALGORITHM}_public_key FROM cryptographic_data LIMIT 1"
                diagnostics_file = "windows_client_diagnostics.txt"
            elif port == LINUX_PORT:
                database = os.getenv("LINUX_CLIENT_DATABASE")
                encryption_query = f"SELECT {ENCRYPTION_ALGORITHM} FROM cryptographic_data LIMIT 1"
                sign_query = f"SELECT server_{SIGNATURE_ALGORITHM}_public_key FROM cryptographic_data LIMIT 1"
                diagnostics_file = "linux_client_diagnostics.txt"

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
                    chunk, ret_val = connection_receive(connection_socket, BYTES_TO_READ) # TODO: Check resource usage and compare between receiving all bytes at once or if splitting it up into 1024 is better for an embedded system
                    if ret_val != SUCCESS:
                        print("Error during connection receive.")
                        return BYTES_NONE, BYTES_NONE, INT_NONE, INT_NONE, STR_NONE, PAYLOAD_RECEIVE_ERROR
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

            print(f"Header: {header}")
            print(f"Nonce length: {len(nonce)}")
            print(f"Nonce: {nonce}")
            print(f"Tag: {tag}")
            print(f"Tag length: {len(tag)}")
            print(f"Identifier: {identifier}")
            print(f"Payload length: {payload_length}")
            print(f"Data type: {data_type}")
            print(f"File name length: {file_name_length}")
            print(f"Data subtype: {data_subtype}")
            print(f"Payload: {payload}")

            
            # TODO: Time all encompassing operations too, not just decryption and verification
            print("Timing security checks ...")
            process = psutil.Process(os.getpid())
            (payload, ret_val), decrypt_stats = measure_operation(process, payload_decryption, payload, nonce, tag, encryption_key)
            if ret_val != SUCCESS:
                print("Error during payload decryption.")
                return BYTES_NONE, BYTES_NONE, INT_NONE, INT_NONE, STR_NONE, PAYLOAD_DECRYPTION_ERROR

            file_name = payload[:file_name_length]

            hash_stats = {}
            sign_stats = {}
            if data_subtype == UPDATE_FILE:
                (data_inb, ret_val), hash_stats = measure_operation(process, verify_hash, payload, file_name_length, payload_length)
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
                db_connection = sqlite3.connect(database)
                cursor = db_connection.cursor()
                if port == SERVER_PORT:
                    public_key = (cursor.execute(sign_query, (identifier,))).fetchone()[0]
                else:
                    public_key = (cursor.execute(sign_query)).fetchone()[0]
                db_connection.close()

                ret_val, sign_stats = measure_operation(process, verify_signature, public_key, payload, payload_length)
                if ret_val == SUCCESS:
                    print("Signature is valid.")
                elif SIGNATURE_INVALID_ERROR:
                    print("Signature is invalid.")
                    return BYTES_NONE, BYTES_NONE, INT_NONE, INT_NONE, STR_NONE, PAYLOAD_RECEIVE_ERROR
                else:
                    print("Error during signature verification.")
                    return BYTES_NONE, BYTES_NONE, INT_NONE, INT_NONE, STR_NONE, PAYLOAD_RECEIVE_ERROR
            else:
                data_inb = payload[file_name_length:payload_length]

            total_time = decrypt_stats['time'] + hash_stats.get('time', 0) + sign_stats.get('time', 0)

            # Use of ChatGPT for creating logging functionality
            with open(diagnostics_file, 'a') as f:
                current_time = datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                f.write(f"----- Received payload diagnostics Log -----\n")
                f.write(f"Date and Time: {current_time}\n")
                f.write(f"Using SECURITY_MODE: {SECURITY_MODE}\n")
                f.write(f"--------------------------------------------\n")
                f.write(f"------ Security Operation Diagnostics ------\n")
                log_section("Decryption", decrypt_stats, f)
                log_section("Hash Verification", hash_stats, f)
                log_section("Signature Verification", sign_stats, f)
                f.write(f"Total time for security operations: {total_time:.9f} sec\n")
                f.write(f"--------------------------------------------\n")
                f.write(f"---------- End of diagnostics Log ----------\n\n\n\n")

            print(f"Security checks completed in {total_time:.9f} seconds.")

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
        file_name_length = len(file_name)

        # Only packs integers for the header
        header = struct.pack(PACK_DATA_COUNT, payload_length, data_type, file_name_length, data_subtype)

        data_to_send = header + nonce + tag + str.encode(identifier) + encrypted_payload
        print(f"Header: {header}")
        print(f"Nonce length: {len(nonce)}")
        print(f"Nonce: {nonce}")
        print(f"Tag: {tag}")
        print(f"Identifier: {identifier}")
        print(f"Payload length: {payload_length}")
        print(f"Data type: {data_type}")
        print(f"File name length: {file_name_length}")
        print(f"Data subtype: {data_subtype}")
        print(f"Payload: {payload}")

        return data_to_send, SUCCESS

    except Exception as e:
        print(f"An error occurred: {e}")
        return BYTES_NONE, PAYLOAD_CREATION_ERROR