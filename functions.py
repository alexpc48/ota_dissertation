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
import random
import constants
import datetime
import psutil
import os
import dotenv
import threading

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
            pass

        if connection_socket.fileno() != -1:
            # Waits until client sends its close_notify
            tls_unwrap = False
            start_time = time.time()
            while time.time() - start_time < 10:  # Wait 10 seconds until timing out
                try:
                    #print("Unwrapping TLS ...")
                    connection_socket = connection_socket.unwrap() # Removes TLS
                    tls_unwrap = True
                    # print("TLS unwrapped.")
                    break
                except ssl.SSLWantReadError:
                    continue
                except ssl.SSLWantWriteError:
                    continue
                except Exception as e:
                    # print(f"An error occurred during socket unwrap: {e}")
                    break
            if tls_unwrap == False:
                # print("TLS unwrap timed out.")
                # print("Abruptly closing socket ...")
                pass
            else:
                print("Closing socket ...")
                pass
            connection_socket.close()
            print("Socket closed.")
        else:
            print("Socket is not open")
            pass

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
        #print(f"Creating listening socket on {host}:{port} ...")
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
        start_time = time.perf_counter()
        
        print("\nAccepting new connection ...")
        _, listening_port = LISTENING_SOCKET_INFO
        if listening_port == SERVER_PORT:
            diagnostics_file = "server_diagnostics.csv"
        elif listening_port == WINDOWS_PORT:
            diagnostics_file = "windows_client_diagnostics.csv"
        elif listening_port == LINUX_PORT:
            diagnostics_file = "linux_client_diagnostics.csv"

        #print("Timing TLS implementation ...")
        process = psutil.Process(os.getpid())
        context_creation_stats, socket_wrap_stats, tls_handshake_stats = {}, {} , {}

        # Context configuration
        _, listening_port = LISTENING_SOCKET_INFO # Format = host, port
        (context, ret_val), context_creation_stats = measure_operation(process, create_context, 'server', listening_port)
        if ret_val == ERROR:
            print("Error creating context.")
            return ERROR

        connection_socket, address = socket.accept()
        print(f"Accepted connection from {address[0]}:{address[1]} ...")
        connection_socket.setblocking(False)

        # Wrap the socket with TLS
        # connection_socket = context.wrap_socket(connection_socket, server_side=True, do_handshake_on_connect=False)
        (connection_socket), socket_wrap_stats = measure_operation(process, context.wrap_socket, connection_socket, server_side=True, do_handshake_on_connect=False)

        # Register the connection with the selector
        data = types.SimpleNamespace(address=address, inb=BYTES_NONE, outb=BYTES_NONE, file_name=STR_NONE, data_subtype=INT_NONE, handshake_complete=False)
        events = selectors.EVENT_READ | selectors.EVENT_WRITE # Allow socket to read and write

        selector.register(connection_socket, events, data=data)
        print(f"Connection from {address[0]}:{address[1]} registered with the selector.")

        # print("Waiting for TLS handshake ...")
        # ret_val = wait_for_TLS_handshake(connection_socket, selector)
        (ret_val), tls_handshake_stats = measure_operation(process, wait_for_TLS_handshake, connection_socket, selector)
        if ret_val != SUCCESS:
            print("Error during TLS handshake.")
            return ERROR
        # print("TLS handshake successful.")

        end_time = time.perf_counter()
        #print(f"Accepting connection completed in {end_time - start_time:.9f} seconds.") # - timeout_interval accounts for the random sleep time
        #print("Writing diagnostics ...")
        security_operations = [context_creation_stats, socket_wrap_stats, tls_handshake_stats]
        _ = write_diagnostic_file('Accepting connection', diagnostics_file, security_operations)
        #print("Diagnostics written.")

        #print(f"Cipher suite: {connection_socket.cipher()}")

        return SUCCESS
    
    except Exception as e:
        print(f"An error occurred: {e}")
        _ = close_connection(connection_socket, selector)
        return CONNECTION_ACCEPT_ERROR
    
# Creates a connection to an endpoint
def create_connection(host: str, port: int, selector: selectors.SelectSelector) -> typing.Tuple[selectors.SelectSelector, ssl.SSLSocket, int]:
    try:
        start_time = time.perf_counter()

        print(f"Initiating connection to {host}:{port} ...")
        _, listening_port = LISTENING_SOCKET_INFO
        if listening_port == SERVER_PORT:
            diagnostics_file = "server_diagnostics.csv"
        elif listening_port == WINDOWS_PORT:
            diagnostics_file = "windows_client_diagnostics.csv"
        elif listening_port == LINUX_PORT:
            diagnostics_file = "linux_client_diagnostics.csv"

        process = psutil.Process(os.getpid())
        context_creation_stats, socket_wrap_stats, do_tls_handshake_stats, tls_handshake_stats = {}, {} , {}, {}

        # Context configuration
        _, listening_port = LISTENING_SOCKET_INFO
        (context, ret_val), context_creation_stats = measure_operation(process, create_context, 'client', listening_port)
        if ret_val == ERROR:
            print("Error creating context.")
            return ERROR

        connection_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connection_socket.setblocking(False)

        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        data = types.SimpleNamespace(address=(host, port), inb=BYTES_NONE, outb=BYTES_NONE, connected=False, file_name=STR_NONE, data_subtype=INT_NONE, handshake_complete=False)
        
        # Waits for the connection to complete in a non-blocking way, but blocks all other operations
        # FIXME: I think there is another err code that I am missing
        connection_attempts = 0
        while not data.connected:
            err = connection_socket.connect_ex((host, port)) # Try connecting
            if err == 10056 or err == SUCCESS: # Connection made
                print(f"Connection to {host}:{port} successful.")
                data.connected = True
                break
            elif err == 10035 or err == errno.EINPROGRESS or err == errno.EALREADY or err == errno.EAGAIN: # Non-blocking connection in progress
                print(f"Connection to {host}:{port} in progress ...")
                time.sleep(1)
                continue
            elif err == 10022 or err == errno.EINVAL or err == errno.EHOSTUNREACH or err == errno.ECONNREFUSED: # Failed connction
                print("No device found at the specified address.")
                # Try up to 5 times to connect to the client
                if connection_attempts > 4:
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

        # Wrap socket with TSL
        # connection_socket = context.wrap_socket(connection_socket, do_handshake_on_connect=False, server_hostname=host) # Wraps the socket with TLS
        (connection_socket), socket_wrap_stats = measure_operation(process, context.wrap_socket, connection_socket, do_handshake_on_connect=False, server_hostname=host) 
        # print("Initiating TLS handshake ...")
        start_time = time.time()
        while time.time() - start_time < 10:  # Wait 10 seconds until timing out
            try:
                connection_socket.do_handshake() # Can't measure the performance of this due to non-blocking nature
                # do_tls_handshake_stats = measure_operation(process, connection_socket.do_handshake)
                data.outb = HANDSHAKE_COMPLETE
                break
            except ssl.SSLWantReadError: # Ignore (non-blocking) error
                # #print("SSLWantReadError during handshake.")
                continue
            except ssl.SSLWantWriteError: # Ignore (non-blocking) error
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

        # print("Waiting for TLS handshake ...")
        # ret_val = wait_for_TLS_handshake(connection_socket, selector)
        (ret_val), tls_handshake_stats = measure_operation(process, wait_for_TLS_handshake, connection_socket, selector)
        if ret_val != SUCCESS:
            print("Error during TLS handshake.")
            return None, None, ERROR
        # print("TLS handshake successful.")

        end_time = time.perf_counter()
        #print(f"Creating connection completed in {end_time - start_time:.9f} seconds.") # - timeout_interval accounts for the random sleep time
        #print("Writing diagnostics ...")
        security_operations = [context_creation_stats, socket_wrap_stats, do_tls_handshake_stats, tls_handshake_stats]
        _ = write_diagnostic_file('Creating Connection', diagnostics_file, security_operations)
        #print("Diagnostics written.")

        #print(f"Cipher suite: {connection_socket.cipher()}")

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
            # #print("SSLWantReadError: Waiting for more data to be readable...")
            continue
    
        except ssl.SSLWantWriteError:
            # #print("SSLWantWriteError: Waiting until socket is writable...")
            continue
    #print("Timeout: No data received within 10 seconds.")
    return BYTES_NONE, TIMEOUT_ERROR

# ChatGPT used to help create a metrics capture for security operations
def measure_operation(process, func, *args, **kwargs):

    peak_rss = [0]

    def monitor_memory():
        while not done[0]:
            rss = process.memory_info().rss
            peak_rss[0] = max(peak_rss[0], rss)
            time.sleep(0.01)  # Sample every 10 ms

    done = [False]
    monitor_thread = threading.Thread(target=monitor_memory)
    monitor_thread.start()

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
    # Stop monitoring
    done[0] = True
    monitor_thread.join()
    snapshot_end = tracemalloc.take_snapshot()
    
    # CPU and memory metrics
    cpu_user = cpu_times_end.user - cpu_times_start.user
    cpu_sys = cpu_times_end.system - cpu_times_start.system
    cpu_total = cpu_user + cpu_sys
    
    mem_rss = mem_info_end.rss - mem_info_start.rss # Resident Set Size (RSS) - total memory used by the process
    # mem_uss = getattr(mem_info_end, 'uss', 0) - getattr(mem_info_start, 'uss', 0) # Unique Set Size (USS) - memory used by the process that is not shared with other processes
    mem_uss = mem_info_end.uss - mem_info_start.uss # Private memory - memory used by the process that is not shared with other processes
    cpu_equiv = cpu_total / elapsed_time if elapsed_time > 0 else 0 # Effective CPU cores used
    py_alloc = sum(stat.size_diff for stat in snapshot_end.compare_to(snapshot_start, 'lineno'))
    _, py_peak = tracemalloc.get_traced_memory()

    return result, {
        "operation": func.__name__,
        "time": elapsed_time,
        "cpu_user": cpu_user,
        "cpu_sys": cpu_sys,
        "cpu_total": cpu_total,
        "cpu_percent": cpu_percent,
        "cpu_equiv": cpu_equiv,
        "mem_rss": mem_rss,
        "mem_uss": mem_uss,
        "py_mem": py_alloc,
        "peak_rss": peak_rss[0],
        "py_mem_peak": py_peak
    }

# Format is for .csv for export capabilties to Excel
# 3 columns
def log_section(name, stats, f):
    if not stats:
        return
    f.write(f"{name} Diagnostics,,\n")
    f.write(f"Time:,{stats['time']:.9f},sec\n")
    f.write(f"CPU time (user):,{stats['cpu_user']:.9f},sec\n")
    f.write(f"CPU time (system):,{stats['cpu_sys']:.9f},sec\n")
    f.write(f"Total CPU time:,{stats['cpu_total']:.9f},sec\n")
    f.write(f"Effective CPU cores used:,{stats['cpu_equiv']:.2f},x\n")
    f.write(f"CPU usage during operation:,{stats['cpu_percent']:.2f},%\n")
    f.write(f"Memory change (RSS):,{stats['mem_rss']},bytes\n")
    f.write(f"Memory change (USS):,{stats['mem_uss']},bytes\n")
    f.write(f"Python memory allocated:,{stats['py_mem']},bytes\n\n")
    if not name == 'download_update':
        return
    f.write(f"Peak memory usage (RSS):,{stats['peak_rss']},bytes\n")
    f.write(f"Peak Python memory usage:,{stats['py_mem_peak']},bytes\n\n")

def write_diagnostic_file(action: str, diagnostics_file: str, security_operations: dict) -> int:
    total_time = 0
    for security_operation in security_operations:
        if security_operation:
            total_time += security_operation['time']

    with open(diagnostics_file, 'a') as f:
        current_time = datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        f.write(f"{action} Diagnostics Log,,\n")
        f.write(f"Date and Time: {current_time},,\n")
        # f.write(f"\n")
        f.write(f"Operation Diagnostics,,\n")
        for security_operation in security_operations:
            if security_operation:
                log_section(security_operation['operation'], security_operation, f)
        f.write(f"Total time for security operations:,{total_time:.9f},sec\n")
        # f.write(f"\n")
        f.write(f"End of diagnostics Log,,\n\n\n\n")
    return SUCCESS

# Receives the payload from the socket
def receive_payload(connection_socket: ssl.SSLSocket) -> typing.Tuple[bytes, bytes, int, int, str, int]:
    try:
        # start_time = time.perf_counter()
        file_name = BYTES_NONE # Initialise variable

        # Read the packet header
        # Receive packed data (integers)
        header, ret_val = connection_receive(connection_socket, PACK_COUNT_BYTES) # Receives the amount of bytes in the struct.pack header
        if ret_val != SUCCESS:
            #print("Error during connection receive.")
            return BYTES_NONE, BYTES_NONE, INT_NONE, INT_NONE, STR_NONE, PAYLOAD_RECEIVE_ERROR
        if header == BYTES_NONE: # Closes connection if no data is received from the remote connection
            #print("No data received.")
            return BYTES_NONE, BYTES_NONE, INT_NONE, INT_NONE, STR_NONE, CONNECTION_CLOSE_ERROR
        #print("Header received.")

        # Continue if data is received
        # Data arrives as header -> nonce -> tag -> identifier -> payload
        # Identifier not sensitive - in application could be the VIN of the vehicle
        if header:
            # Receive other sub-header information
            #print("Receiving nonce ...")
            nonce, ret_val = connection_receive(connection_socket, NONCE_LENGTH)
            if ret_val != SUCCESS:
                #print("Error during connection receive.")
                return BYTES_NONE, BYTES_NONE, INT_NONE, INT_NONE, STR_NONE, PAYLOAD_RECEIVE_ERROR
            #print("Nonce received.")
            #print("Receiving tag ...")
            tag, ret_val = connection_receive(connection_socket, TAG_LENGTH)
            if ret_val != SUCCESS:
                #print("Error during connection receive.")
                return BYTES_NONE, BYTES_NONE, INT_NONE, INT_NONE, STR_NONE, PAYLOAD_RECEIVE_ERROR
            #print("Tag received.")
            #print("Receiving identifier ...")
            identifier, ret_val = connection_receive(connection_socket, IDENTIFIER_LENGTH)
            if ret_val != SUCCESS:
                #print("Error during connection receive.")
                return BYTES_NONE, BYTES_NONE, INT_NONE, INT_NONE, STR_NONE, PAYLOAD_RECEIVE_ERROR
            identifier = identifier.decode()
            #print("Identifier received.")

            # Uses listening port to determine which database to use
            _, port = LISTENING_SOCKET_INFO
            dotenv.load_dotenv()
            if port == SERVER_PORT:
                database = os.getenv("SERVER_DATABASE")
                encryption_query = f"SELECT {ENCRYPTION_ALGORITHM} FROM vehicles WHERE vehicle_id = ? LIMIT 1" # (identifier,)
                sign_query = f"SELECT {SIGNATURE_ALGORITHM}_public_key FROM vehicles WHERE vehicle_id = ? LIMIT 1" # (identifier,)
                diagnostics_file = "server_diagnostics.csv"
            elif port == WINDOWS_PORT:
                database = os.getenv("WINDOWS_CLIENT_DATABASE")
                encryption_query = f"SELECT {ENCRYPTION_ALGORITHM} FROM cryptographic_data LIMIT 1"
                sign_query = f"SELECT server_{SIGNATURE_ALGORITHM}_public_key FROM cryptographic_data LIMIT 1"
                diagnostics_file = "windows_client_diagnostics.csv"
            elif port == LINUX_PORT:
                database = os.getenv("LINUX_CLIENT_DATABASE")
                encryption_query = f"SELECT {ENCRYPTION_ALGORITHM} FROM cryptographic_data LIMIT 1"
                sign_query = f"SELECT server_{SIGNATURE_ALGORITHM}_public_key FROM cryptographic_data LIMIT 1"
                diagnostics_file = "linux_client_diagnostics.csv"

            # Retrieve symmetric encrypion key
            #print(f"Retrieving encryption key from {database} ...")z
            db_connection = sqlite3.connect(database)
            cursor = db_connection.cursor()
            if port == SERVER_PORT:
                encryption_key = (cursor.execute(encryption_query, (identifier,))).fetchone()[0]
            else:
                encryption_key = (cursor.execute(encryption_query)).fetchone()[0]
            db_connection.close()
            #print("Retrieved encryption key.")
                    
            # Unpack the header
            #print("Unpacking header ...")
            payload_length, data_type, file_name_length, data_subtype = struct.unpack(PACK_DATA_COUNT, header[:PACK_COUNT_BYTES])
            #print("Header unpacked.")

            #print("Receiving payload ...")
            payload = BYTES_NONE # Initialise variable
            while len(payload) < payload_length:
                try:
                    chunk, ret_val = connection_receive(connection_socket, BYTES_TO_READ)
                    if ret_val != SUCCESS:
                        #print("Error during connection receive.")
                        return BYTES_NONE, BYTES_NONE, INT_NONE, INT_NONE, STR_NONE, PAYLOAD_RECEIVE_ERROR
                except BlockingIOError as e:
                    #print(f"BlockingIOError: {e}")
                    if e.errno == errno.EAGAIN:
                        #print("Resource temporarily unavailable. Retrying ...")
                        time.sleep(1) # Wait for a second before retrying
                        continue
                if not chunk:
                    #print("Connection closed before receiving the full payload.")
                    return BYTES_NONE, BYTES_NONE, INT_NONE, INT_NONE, STR_NONE, INCOMPLETE_PAYLOAD_ERROR
                payload += chunk
            #print("Payload received.")
            
            #print("Timing security checks ...")
            process = psutil.Process(os.getpid())
            decryption_stats, hash_verification_stats, signature_verification_stats = {}, {} , {}

            (payload, ret_val), decryption_stats = measure_operation(process, payload_decryption, payload, nonce, tag, encryption_key)
            if ret_val != SUCCESS:
                print("Error during payload decryption.")
                return BYTES_NONE, BYTES_NONE, INT_NONE, INT_NONE, STR_NONE, PAYLOAD_DECRYPTION_ERROR
            # print("Payload decrypted.")
            print(f"Payload: {payload}")

            file_name = payload[:file_name_length]

            if data_subtype == UPDATE_FILE:
                (data_inb, ret_val), hash_verification_stats = measure_operation(process, verify_hash, payload, file_name_length, payload_length)
                if ret_val == SUCCESS:
                    # print("Hash is valid.")
                    pass
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

                ret_val, signature_verification_stats = measure_operation(process, verify_signature, public_key, payload, payload_length)
                if ret_val == SUCCESS:
                    # print("Signature is valid.")
                    pass
                elif SIGNATURE_INVALID_ERROR:
                    print("Signature is invalid.")
                    return BYTES_NONE, BYTES_NONE, INT_NONE, INT_NONE, STR_NONE, PAYLOAD_RECEIVE_ERROR
                else:
                    print("Error during signature verification.")
                    return BYTES_NONE, BYTES_NONE, INT_NONE, INT_NONE, STR_NONE, PAYLOAD_RECEIVE_ERROR
            else:
                data_inb = payload[file_name_length:payload_length]

            # end_time = time.perf_counter()
            # print(f"Receiving payload completed in {end_time - start_time:.9f} seconds.")
            #print("Writing diagnostics ...")
            security_operations = [decryption_stats, hash_verification_stats, signature_verification_stats]
            _ = write_diagnostic_file('Receiving Payload', diagnostics_file, security_operations)
            #print("Diagnostics written.")

            return file_name, data_inb, data_type, data_subtype, identifier, SUCCESS


    except Exception as e:
        print(f"An error occurred: {e}")
        return BYTES_NONE, BYTES_NONE, INT_NONE, INT_NONE, STR_NONE, PAYLOAD_RECEIVE_ERROR

def create_payload(data_to_send: bytes, file_name: bytes, data_subtype: int, encryption_key: bytes) -> typing.Tuple[bytes, int]:
    try:
        # start_time = time.perf_counter()

        # Query for getting relevant database
        dotenv.load_dotenv()
        _, port = LISTENING_SOCKET_INFO
        if port == SERVER_PORT:
            database = os.getenv("SERVER_DATABASE")
            diagnostics_file = "server_diagnostics.csv"
        elif port == WINDOWS_PORT:
            database = os.getenv("WINDOWS_CLIENT_DATABASE")
            diagnostics_file = "windows_client_diagnostics.csv"
        elif port == LINUX_PORT:
            database = os.getenv("LINUX_CLIENT_DATABASE")
            diagnostics_file = "linux_client_diagnostics.csv"

        # Gets the senders identifier
        db_connection = sqlite3.connect(database)
        cursor = db_connection.cursor()
        identifier = (cursor.execute("SELECT identifier FROM network_information WHERE network_id = 1")).fetchone()[0]
        db_connection.close()

        # Determines if the data to be sent is just a status response or request, or it is actual data
        if data_to_send in vars(constants).values() and not data_subtype: # Checks if the data to send is defined in the constants file
            data_type = STATUS_CODE
        else:
            data_type = DATA

        # Keeps the same header format even if endpoint is not sending a file
        if not file_name or type(file_name) == str:
            file_name = BYTES_NONE

        payload = file_name + data_to_send

        #print("Timing security implementation ...")
        process = psutil.Process(os.getpid())
        encryption_stats, hash_generation_stats, signature_generation_stats = {}, {} , {}

        # Security relating to update files, not response or request communications
        if data_subtype == UPDATE_FILE:
            update_file = data_to_send
            # update_file_hash, ret_val = generate_hash(update_file)
            (update_file_hash, ret_val), hash_generation_stats = measure_operation(process, generate_hash, update_file)
            if ret_val == ERROR:
                print("Error during hash generation.")
                return BYTES_NONE, PAYLOAD_CREATION_ERROR
            # print("Hash generated.")
            payload += update_file_hash

            db_connection = sqlite3.connect(database)
            cursor = db_connection.cursor()
            private_key = (cursor.execute(f"SELECT {SIGNATURE_ALGORITHM}_private_key FROM cryptographic_data WHERE cryptographic_entry_id = 1")).fetchone()[0]
            db_connection.close()

            (payload, ret_val), signature_generation_stats = measure_operation(process, generate_signature, payload, private_key)
            if ret_val == ERROR:
                print("Error during signature generation.")
                return BYTES_NONE, PAYLOAD_CREATION_ERROR
            # print("Signature generated.")
                    
        (nonce, encrypted_payload, tag, ret_val), encryption_stats = measure_operation(process, payload_encryption, payload, encryption_key)
        if ret_val != SUCCESS:
            print("Error during payload encryption.")
            return BYTES_NONE, PAYLOAD_ENCRYPTION_ERROR
        # print("Payload encrypted.")

        payload_length = len(encrypted_payload)

        # Only packs integers for the header
        header = struct.pack(PACK_DATA_COUNT, payload_length, data_type, len(file_name), data_subtype)

        data_to_send = header + nonce + tag + str.encode(identifier) + encrypted_payload

        # end_time = time.perf_counter()
        #print(f"Creating payload completed in {end_time - start_time:.9f} seconds.")
        #print("Writing diagnostics ...")
        security_operations = [encryption_stats, hash_generation_stats, signature_generation_stats]
        _ = write_diagnostic_file('Creating Payload', diagnostics_file, security_operations)
        #print("Diagnostics written.")

        return data_to_send, SUCCESS

    except Exception as e:
        print(f"An error occurred: {e}")
        return BYTES_NONE, PAYLOAD_CREATION_ERROR