# HEADER FILE

# Libraries
import sys
import socket
import typing
import selectors
import threading
import os
import types
import errno
import time
import sqlite3
import dotenv
from constants import *

# Global variables
database = None

def options_menu() -> str:
    print("\n-------------------------------------------------------------------------------------------")
    print("Options:")
    print("-------------------------------------------------------------------------------------------")
    print("1. Push the latest update to the client")
    print("-------------------------------------------------------------------------------------------")
    print("10. Get the client update readiness status") # TODO
    print("11. Get the client update status") # TODO: Check if the update has been installed, failed, behind, etc.
    print("12. Get the client update version") # TODO
    print("-------------------------------------------------------------------------------------------")
    print("20. Change the update file") # TODO
    print("-------------------------------------------------------------------------------------------")
    print("98. Redisplay the options menu")
    print("99. Exit")
    print("-------------------------------------------------------------------------------------------")

    return input("Enter an option: ")

def create_listening_socket(host: str, port: int, selector: selectors.SelectSelector) -> int:
    try:
        print(f"Creating listening socket on {host}:{port} ...")
        listening_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listening_socket.bind((host, port))
        listening_socket.listen()
        listening_socket.setblocking(False)

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
        data = types.SimpleNamespace(address=address, inb=b"", outb=b"")
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
        data = types.SimpleNamespace(address=(host, port), inb=b"", outb=b"", connected=False)
        
        # Waits for the connection to complete (blocks all other operations)
        connection_attempts = 0
        while not data.connected:
            err = connection_socket.connect_ex((host, port)) # Try connecting to the client
            print("[SYN]")
            if err == 10056: # Connection made
                print(f"Connection to {host}:{port} successful.")
                data.connected = True
                print("[SYN-ACK]")
                break
            elif err == 10035: # Non-blocking connection in progress
                print(f"Connection to {host}:{port} in progress ...")
                continue
            elif err == 10022: # Failed connction (no client at the address)
                print("No client found at the specified address.")
                # Try up to 5 times to connect to the client
                if connection_attempts > 5:
                    print("Connection attempts exceeded. Exiting ...")
                    return CONNECTION_INITIATE_ERROR
                print("Trying again ...")
                time.sleep(5)
                connection_attempts += 1
                continue
            else:
                print(f"Connection to {host}:{port} failed with error: {errno.errorcode[err]}\n")
                print("Please check the host and port details.")
                return CONNECTION_INITIATE_ERROR

        # Register the connection with the selector for read and write events
        selector.register(connection_socket, events, data=data)
        print("Socket registered.")

        return selector, connection_socket, SUCCESS
    
    except Exception as e:
        print(f"An error occurred: {e}")
        _ = close_connection(connection_socket, selector)
        return _, CONNECTION_INITIATE_ERROR


def push_update(selector: selectors.SelectSelector, response_event: threading.Event, response_data: dict) -> int:
    try:
        dotenv.load_dotenv()
        database = os.getenv("SERVER_DATABASE", "server_ota_updates.db")

        db_connection = sqlite3.connect(database)
        cursor = db_connection.cursor()
        query_result = (cursor.execute("SELECT vehicles_entry_id, vehicle_id, vehicle_ip, vehicle_port FROM vehicles ORDER BY vehicles_entry_id")).fetchall()
        db_connection.close()

        print("Vehicle entries in the database.")
        for result in query_result:
            print("Vehicle Entry ID: ", result[0])
            print("Vehicle ID: ", result[1])
            print("Vehicle IP: ", result[2])
            print("Vehicle Port: ", result[3])
        
        vehicle_id_input = int(input("Enter the vehicle ID to push the update to: "))

        # AI help for next() function
        selected_vehicle = next((v for v in query_result if v[0] == vehicle_id_input), None)

        client_host = selected_vehicle[2]
        client_port = selected_vehicle[3]

        selector, connection_socket, ret_val = create_connection(client_host, client_port, selector)
        if ret_val == SUCCESS:
            print("Connection to client established.")
        elif ret_val == CONNECTION_INITIATE_ERROR:
            print("Error: Connection initiation failed.")
            return CONNECTION_INITIATE_ERROR
        else:
            print("An error occurred while establishing the connection.")
            return ERROR

        key = selector.get_key(connection_socket)

        print('Preparing data to send ...')
        key.data.outb = UPDATE_READINESS_REQUEST
        print('Data ready to send.')

        response_event.clear()
        response_event.wait(timeout=None)
        if not response_event.is_set():
            print("Timeout waiting for client response.")
            return CONNECTION_SERVICE_ERROR
        
        if response_data.get("update_readiness") == False:
            print("Client is not ready to receive the update.")
            return CLIENT_NOT_UPDATE_READY_ERROR
        
        response_data.clear()  # Clear the response data for the next request
        response_event.clear() # Clear the event for the next request
        print("Pushed update successfully.")
        return SUCCESS
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return ERROR

# TODO: Needs to check latest update in database and compare with what is said the client has
def check_for_updates() -> typing.Tuple[bool, bytes, int]:
    update_available = True
    update_available_bytes = UPDATE_AVALIABLE
    return update_available, update_available_bytes, SUCCESS

# TODO: https://chatgpt.com/share/67e81027-c6bc-800e-adbc-2086ecf38797
# TODO: Use dedicated header file with more information
def get_update_file() -> typing.Tuple[bytes, int]:
    try:
        dotenv.load_dotenv()
        database = os.getenv("SERVER_DATABASE", "server_ota_updates.db")

        print("Preparing update file ...")
        db_connection = sqlite3.connect(database)
        cursor = db_connection.cursor()
        # Gets the latest update file from the database
        update_version, update_file = (cursor.execute("SELECT update_version, update_file FROM updates ORDER BY update_id DESC LIMIT 1")).fetchone()
        db_connection.close()

        file_data = str.encode(update_version) + FILE_HEADER_SECTION_END + update_file + EOF_TAG_BYTE + RECEIVED_FILE_CHECK_REQUEST
        return file_data, SUCCESS
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return ERROR

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