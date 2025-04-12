# HEADER FILE
# Common functions for both the server and client

# Libraries
import socket
import selectors
import struct
import types
import typing
import errno
import random
import sqlite3
import os
import time
import constants
from constants import *
from cryptographic_functions import *

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
    
LISTENING_SOCKET_INFO = None # Global variable to store the listening socket information
def create_listening_socket(host: str, port: int, selector: selectors.SelectSelector) -> int:
    global LISTENING_SOCKET_INFO
    try:
        print(f"Creating listening socket on {host}:{port} ...")
        listening_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listening_socket.bind((host, port))
        listening_socket.listen()
        listening_socket.setblocking(False)

        LISTENING_SOCKET_INFO = listening_socket.getsockname()
        print(LISTENING_SOCKET_INFO)

        # Register the listening socket with the selector
        selector.register(listening_socket, selectors.EVENT_READ, data="listening_socket")
        print(f"Listening on {host}:{port} for connections ...")
        return SUCCESS
    
    except Exception as e:
        print(f"An error occurred: {e}")
        _ = close_connection(listening_socket, selector)
        return LISTENING_SOCKET_CREATION_ERROR
    
def accept_new_connection(socket: socket.socket, selector: selectors.SelectSelector) -> int:
    try:
        print("Accepting new connection ...")
        connection_socket, address = socket.accept()
        print(f"Accepted connection from {address[0]}:{address[1]} ...")
        connection_socket.setblocking(False)

        # Register the connection with the selector
        data = types.SimpleNamespace(address=address, inb=b"", outb=b"", file_name=STR_NONE, data_subtype=INT_NONE)
        events = selectors.EVENT_READ | selectors.EVENT_WRITE # Allow socket to read and write
        selector.register(connection_socket, events, data=data)
        print(f"Connection from {address[0]}:{address[1]} registered with the selector.")
        print("[ACK]")
        return SUCCESS
    
    except Exception as e:
        print(f"An error occurred: {e}")
        _ = close_connection(connection_socket, selector)
        return CONNECTION_ACCEPT_ERROR
    
def create_connection(host: str, port: int, selector: selectors.SelectSelector) -> typing.Tuple[selectors.SelectSelector, socket.socket, int]:
    try:
        print(f"Initiating connection to {host}:{port} ...")

        connection_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connection_socket.setblocking(False)

        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        data = types.SimpleNamespace(address=(host, port), inb=b"", outb=b"", connected=False, file_name=STR_NONE, data_subtype=INT_NONE)
        
        # Waits for the connection to complete (blocks all other operations)
        connection_attempts = 0
        timeout_interval = random.randint(1, 10)
        time.sleep(timeout_interval) # Refreshes in random intervals to avoid collisions
        while not data.connected:
            err = connection_socket.connect_ex((host, port)) # Try connecting
            print("[SYN]")
            if err == 10056 or err == SUCCESS: # Connection made
                print(f"Connection to {host}:{port} successful.")
                data.connected = True
                print("[SYN-ACK]")
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

        # Register the connection with the selector for read and write events
        selector.register(connection_socket, events, data=data)
        print("Socket registered.")

        return selector, connection_socket, SUCCESS
    
    except Exception as e:
        print(f"An error occurred: {e}")
        _ = close_connection(connection_socket, selector)
        return None, None, CONNECTION_INITIATE_ERROR

def receive_payload(connection_socket: socket.socket) -> typing.Tuple[bytes, bytes, int, int, str, int]:
    try:
        file_name = BYTES_NONE # Initialise variable

        # Read the packet header
        # Receive packed data (integers)
        print("Receiving header ...")
        header = connection_socket.recv(PACK_COUNT_BYTES)
        print(f"Header: {header}")
        if header == BYTES_NONE: # Closes connection if no data is received from the remote connection
            print("No data received.")
            return BYTES_NONE, BYTES_NONE, INT_NONE, INT_NONE, STR_NONE, CONNECTION_CLOSE_ERROR

        # Continue if data is received
        # Data arrives as header -> nonce -> tag -> identifier -> payload
        # Identifier not sensitive - in application could be the VIN
        if header:
            # Receive the nonce and tag
            print("Receiving nonce and tag ...")
            nonce = connection_socket.recv(NONCE_LENGTH)
            print(f"Nonce: {nonce}")
            tag = connection_socket.recv(TAG_LENGTH)
            print(f"Tag: {tag}")
            
            identifier = (connection_socket.recv(IDENTIFIER_LENGTH)).decode()
            print(f"Identifier: {identifier}")

            _, port = LISTENING_SOCKET_INFO
            if port == SERVER_PORT:
                database = os.getenv("SERVER_DATABASE")
                query = f"SELECT {ENCRYPTION_ALGORITHM} FROM vehicles WHERE vehicle_id = '{identifier}' LIMIT 1"
            elif port == WINDOWS_PORT:
                database = os.getenv("WINDOWS_CLIENT_DATABASE")
                query = f"SELECT {ENCRYPTION_ALGORITHM} FROM cryptographic_data LIMIT 1"
            elif port == LINUX_PORT:
                database = os.getenv("LINUX_CLIENT_DATABASE")
                query = f"SELECT {ENCRYPTION_ALGORITHM} FROM cryptographic_data LIMIT 1"

            # Retrieve key based on the encryption algorithm
            print(f"Retrieving encryption key from {database} ...")
            db_connection = sqlite3.connect(database)
            cursor = db_connection.cursor()
            encryption_key = (cursor.execute(query)).fetchone()[0]
            db_connection.close()
                    
            # Unpack the header
            payload_length, data_type, file_name_length, data_subtype = struct.unpack(PACK_DATA_COUNT, header[:PACK_COUNT_BYTES])

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

            # print(f"Payload: {payload}")
            # print(f"Nonce: {nonce}")
            # print(f"Tag: {tag}")
            
            payload, ret_val = payload_decryption(payload, nonce, tag, encryption_key) # Decrypt the payload
            if ret_val != SUCCESS:
                print("Error during payload decryption.")
                return BYTES_NONE, BYTES_NONE, INT_NONE, INT_NONE, STR_NONE, PAYLOAD_DECRYPTION_ERROR
            
            file_name = payload[:file_name_length]
            data_inb = payload[file_name_length:]
            print(f"File name: {file_name}")
            print(f"Payload: {data_inb}")

            return file_name, data_inb, data_type, data_subtype, identifier, SUCCESS

    except Exception as e:
        print(f"An error occurred: {e}")
        return BYTES_NONE, BYTES_NONE, INT_NONE, INT_NONE, STR_NONE, PAYLOAD_RECEIVE_ERROR

def create_payload(data_to_send: bytes, file_name: bytes, data_subtype: int, encryption_key: bytes) -> typing.Tuple[bytes, int]:
    try:
        if data_to_send in vars(constants).values(): # Check if the payload is a constant
            data_type = STATUS_CODE
        else:
            data_type = DATA

        # Keeps the same header format even if client is not sending a file
        if not file_name or type(file_name) == str:
            file_name = BYTES_NONE

        payload = file_name + data_to_send
        payload_length = len(payload)

        print(f'Payload to send: {payload}')

        # Only packs integers for the header
        header = struct.pack(PACK_DATA_COUNT, payload_length, data_type, len(file_name), data_subtype)
        
        nonce, encrypted_payload, tag, ret_val = payload_encryption(payload, encryption_key)
        if ret_val != SUCCESS:
            print("Error during payload encryption.")
            return BYTES_NONE, PAYLOAD_ENCRYPTION_ERROR

        # print(f"Payload: {encrypted_payload}")
        # print(f"Nonce: {nonce}")
        # print(f"Tag: {tag}")

        # Retrieve identifier
        _, port = LISTENING_SOCKET_INFO
        if port == SERVER_PORT:
            database = os.getenv("SERVER_DATABASE")
        elif port == WINDOWS_PORT:
            database = os.getenv("WINDOWS_CLIENT_DATABASE")
        elif port == LINUX_PORT:
            database = os.getenv("LINUX_CLIENT_DATABASE")

        db_connection = sqlite3.connect(database)
        cursor = db_connection.cursor()
        identifier = (cursor.execute("SELECT identifier FROM network_information WHERE network_id = 1")).fetchone()[0]
        db_connection.close()

        data_to_send = header + nonce + tag + str.encode(identifier) + encrypted_payload

        # print(data_to_send)

        return data_to_send, SUCCESS

    except Exception as e:
        print(f"An error occurred: {e}")
        return BYTES_NONE, PAYLOAD_CREATION_ERROR