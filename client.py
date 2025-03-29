# Libraries
import sys
import socket
import selectors
import threading
import os
import types
import errno
import time

from constants import *
from functions import *

# FUNCTIONS
# Function to display the options menu
def options_menu() -> int:
    print("\n-------------------------------------------------------------------------------------------")
    print("Options:")
    print("-------------------------------------------------------------------------------------------")
    print("1. Check for an update") # Checks the server for an update it
    print("2. Download updates") # Downloads the updates from the server
    print("-------------------------------------------------------------------------------------------")
    print("10. Change the update readiness status") # Changes the update readiness status
    print("-------------------------------------------------------------------------------------------")
    print("20. Display the update readiness status") # Displays the current update readiness status
    print("21. Display the update version") # Displays the current update version TODO: Implement properly for database
    print("-------------------------------------------------------------------------------------------")
    print("98. Redisplay the options menu") # Redisplays the options menu
    print("-------------------------------------------------------------------------------------------")
    print("99. Exit")
    print("-------------------------------------------------------------------------------------------")

    return input("Enter an option: ")

# (Use of AI) Thread for displaying the options menu in a non-blocking way
def menu_thread() -> None:
    try:
        while True:
            option = options_menu()
            if option:
                match option:
                    case '1': # Request update from the server
                        print("Checking for updates ...")
                        _, _ = check_for_update(server_host, server_port)
                    case '2': # Download updates from the server
                        print("Downloading updates ...")
                        ret_val = download_update(server_host, server_port)
                        if ret_val == UPDATE_NOT_AVALIABLE:
                            print("No updates available to download.")
                        elif ret_val == CLIENT_NOT_UPDATE_READY_ERROR:
                            print("Client is not ready to receive the update.")
                    case '10': # Change the update readiness status
                        print("Changing update readiness status ...")
                        ret_val = change_update_readiness()
                        if ret_val == SUCCESS:
                            print("Update readiness status changed successfully.")
                        elif ret_val == UPDATE_STATUS_REPEAT_ERROR:
                            pass
                        else:
                            print("Failed to change update readiness status")
                    case '20':
                        db_connection = sqlite3.connect(database)
                        cursor = db_connection.cursor()
                        update_readiness_status = bool((cursor.execute("SELECT update_readiness_status FROM update_information WHERE update_entry_id = 1")).fetchone()[0])
                        db_connection.close()
                        print(f"Update readiness status: {update_readiness_status}")
                    case '21':
                        db_connection = sqlite3.connect(database)
                        cursor = db_connection.cursor()
                        update_version = (cursor.execute("SELECT update_version FROM update_information WHERE update_entry_id = 1")).fetchone()[0]
                        db_connection.close()
                        print(f"Update version: {update_version}")
                    case '98': # Redisplay the options menu
                        continue
                    case '99': # Exit the program
                        print("Exiting ...")
                        break
                    case _:
                        print("Invalid option selected.")
        os._exit(SUCCESS)

    except KeyboardInterrupt:
        print("Exiting due to keyboard interrupt ...")
        os._exit(KEYBOARD_INTERRUPT)

    except Exception as e:
        print(f"An error occurred: {e}")
        os._exit(ERROR)

# Function to create a listening socket for the server to connect to
def create_listening_socket(host: str, port: int, selector: selectors.SelectSelector) -> int:
    try:
        listening_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listening_socket.bind((host, port))
        listening_socket.listen()
        print(f"Listening on {host}:{port} for server connections ...")
        listening_socket.setblocking(False)

        # Register the listening socket with the selector
        selector.register(listening_socket, selectors.EVENT_READ, data="listening_socket")
        return SUCCESS
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return LISTENING_SOCKET_CREATION_ERROR
    
# Change the update readiness status of the client
def change_update_readiness() -> int:
    try:
        db_connection = sqlite3.connect(database)
        cursor = db_connection.cursor()
        update_readiness_status = bool((cursor.execute("SELECT update_readiness_status FROM update_information WHERE update_entry_id = 1")).fetchone()[0])
        
        print(f"Readiness status currently: {update_readiness_status}")
        update_readiness_change_value = str(input("Enter new readiness status (True/False): "))
        if update_readiness_change_value == str(update_readiness_status):
            print(f"Update readiness status is already set to {update_readiness_status}.")
            return ERROR
        elif update_readiness_change_value in ['True', 'False']: # Check if the input is valid
            print("Changing update readiness status ...")

        if update_readiness_change_value == 'True':
            update_readiness_status = int(True)
        elif update_readiness_change_value == 'False':
            update_readiness_status = int(False)
        
        cursor.execute("UPDATE update_information SET update_readiness_status = ? WHERE update_entry_id = 1", (update_readiness_status,))
        db_connection.commit()
        db_connection.close()

        print(f"Update readiness status changed to {update_readiness_status}.")
        return SUCCESS
    except Exception as e:
        print(f"An error occurred: {e}")
        return ERROR

# Funtion accepts new connections and registers them with the selector
def accept_new_connection(socket: socket.socket, selector: selectors.SelectSelector) -> int:
    try:
        # Get socket information
        connection_socket, address = socket.accept()
        print(f"Accepted connection from {address[0]}:{address[1]} ...")
        connection_socket.setblocking(False)

        # Register the connection with the selector
        data = types.SimpleNamespace(address=address, inb=b"", outb=b"")
        events = selectors.EVENT_READ | selectors.EVENT_WRITE # Allow socket to read and write
        selector.register(connection_socket, events, data=data)
        print(f"Connection from {address[0]}:{address[1]} registered with the selector.")
        print('[ACK] recieved')
        return SUCCESS
    
    except BlockingIOError:
        # Handle non-blocking socket operation errors ([WinError 10035])
        print("Non-blocking operation could not be completed immediately. Retrying ...")
        return WAITING_ERROR
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return CONNECTION_ACCEPT_ERROR

# Loop for listening for connections from the server
def listen(selector: selectors.SelectSelector) -> int:
    try:
        while True:
            # Get list of events from the selector
            events = selector.select(timeout=None)
            if events:
                for key, _ in events:
                    # If the event comes from the listening socket, accept the new connection
                    if key.data == "listening_socket":
                        _ = accept_new_connection(key.fileobj, selector)
    except Exception as e:
        print(f"An error occurred: {e}")
        os._exit(LISTENING_ERROR)

# Request an update, if any, from the server
def check_for_update(server_host: str, server_port: int) -> int:
    try:
        print(f"Initiating connection to {server_host}:{server_port} ...")

        connection_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connection_socket.setblocking(False)

        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        data = types.SimpleNamespace(address=(server_host, server_port), inb=b"", outb=b"", connected=False)
        
        # Wait for the connection to complete (blocks all other operations)
        connection_attempts = 0
        while not data.connected:
            err = connection_socket.connect_ex((server_host, server_port)) # Try connecting to the client
            print('[SYN] sent')
            if err == 10056: # Connection made
                print(f"Connection to {server_host}:{server_port} successful.")
                data.connected = True
                print('[SYN-ACK] received')
                break
            elif err == 10035:
                print(f"Connection to {server_host}:{server_port} in progress ...")
                continue
            elif err == 10022: # Tried 5 times to connect then fails
                print("No client found at the specified address.")
                if connection_attempts > 5:
                    print("Connection attempts exceeded. Exiting ...")
                    return CONNECTION_INITIATE_ERROR
                print("Trying again ...")
                time.sleep(5)
                connection_attempts += 1
                continue
            else:
                print(f"Connection to {server_host}:{server_port} failed with error: {errno.errorcode[err]}\n")
                print("Please check the client IP and port.")
                return CONNECTION_INITIATE_ERROR
            
            
        # Register the connection with the selector for read and write events
        selector.register(connection_socket, events, data=data)
                    
        print('Preparing data to send ...')
        data.outb = UPDATE_CHECK_REQUEST
        print('Data ready to send.')

        # Wait for the response to be processed by service_connection
        response_event.clear()
        response_event.wait(timeout=None)  # Wait for up to 10 seconds
        if not response_event.is_set():
            print("Timeout waiting for server response.")
            return CONNECTION_SERVICE_ERROR
        
        if response_data.get("update_available"):
            print("There is an update ready.")
        elif not response_data.get("update_available"):
            print("There is no update ready.")
        update_avaliable = response_data.get("update_available")

        response_data.clear()  # Clear the response data for the next request
        print("Update check request processed successfully.")
        return update_avaliable, SUCCESS
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return CHECK_UPDATE_ERROR

# Download the update from the server (checks first to see if there is an update)
# TODO: Should check if the client is ready to receive the update before downloading it
def download_update(server_host: str, server_port: int) -> int:
    update_available, _ = check_for_update(server_host, server_port)
    if not update_available:
        print("No update available to download.")
        return UPDATE_NOT_AVALIABLE
    
    try:
        print("Checking if the client is ready to receive the update ...")
        db_connection = sqlite3.connect(database)
        cursor = db_connection.cursor()
        update_readiness_status = bool((cursor.execute("SELECT update_readiness_status FROM update_information WHERE update_entry_id = 1")).fetchone()[0])
        
        print(f"Readiness status currently: {update_readiness_status}")

        if update_readiness_status == False:
            print("Client is not ready to receive the update.")
            db_connection.close()
            return CLIENT_NOT_UPDATE_READY_ERROR

        print(f"Initiating connection to {server_host}:{server_port} ...")

        connection_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connection_socket.setblocking(False)

        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        data = types.SimpleNamespace(address=(server_host, server_port), inb=b"", outb=b"", connected=False)
        
        # Wait for the connection to complete (blocks all other operations)
        connection_attempts = 0
        while not data.connected:
            err = connection_socket.connect_ex((server_host, server_port)) # Try connecting to the client
            print('[SYN] sent')
            if err == 10056: # Connection made
                print(f"Connection to {server_host}:{server_port} successful.")
                data.connected = True
                print('[SYN-ACK] received')
                break
            elif err == 10035:
                print(f"Connection to {server_host}:{server_port} in progress ...")
                continue
            elif err == 10022: # Tried 5 times to connect then fails
                print("No client found at the specified address.")
                if connection_attempts > 5:
                    print("Connection attempts exceeded. Exiting ...")
                    return CONNECTION_INITIATE_ERROR
                print("Trying again ...")
                time.sleep(5)
                connection_attempts += 1
                continue
            else:
                print(f"Connection to {server_host}:{server_port} failed with error: {errno.errorcode[err]}\n")
                print("Please check the client IP and port.")
                return CONNECTION_INITIATE_ERROR

        # Register the connection with the selector for read and write events
        selector.register(connection_socket, events, data=data)
                    
        print('Preparing data to send ...')
        data.outb = UPDATE_DOWNLOAD_REQUEST
        print('Data ready to send.')

        # Wait for the response to be processed by service_connection
        response_event.clear()
        response_event.wait(timeout=None)  # Wait for up to 10 seconds
        if not response_event.is_set():
            print("Timeout waiting for server response.")
            return CONNECTION_SERVICE_ERROR

        response_data.clear()  # Clear the response data for the next request
        print("Update downloaded successfully.")
        return SUCCESS
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return DOWNLOAD_UPDATE_ERROR







# Main program
if __name__=='__main__':
    # Usage
    # if len(sys.argv) != 5:
    #     print("Usage: python3 client.py <local_host> <local_port> <server_host> <server_port>")
    #     sys.exit(ERROR)

    # Create a selector object
    selector = selectors.DefaultSelector()

    # Assign variables from arguments
    local_host, local_port, database = sys.argv[1], int(sys.argv[2]), sys.argv[3]

    db_connection = sqlite3.connect(database)
    cursor = db_connection.cursor()
    result = (cursor.execute("SELECT server_ip, server_port FROM network_information ORDER BY network_id DESC LIMIT 1")).fetchone()
    server_host, server_port = result[0], result[1]
    db_connection.close()
    
    # Create listening socket so that the server can connect forcefully (i.e, push updates to client)
    ret_val = create_listening_socket(local_host, local_port, selector)
    if ret_val != SUCCESS:
        print('Failed to create listening socket')
        sys.exit(ret_val)

    # THREADS
    # TODO Ensure threads are closed/finished correctly and fully
    # Start the menu thread
    options_menu_thread = threading.Thread(target=menu_thread, daemon=False)

    # Listening loop
    listen_thread = threading.Thread(target=listen, daemon=False, args=(selector,))
    
    # Servicing loop
    response_event = threading.Event()
    response_data = {}
    service_connection_thread = threading.Thread(target=service_connection, daemon=False, args=(selector, response_event, response_data, database))

    # Start the threads
    options_menu_thread.start()
    listen_thread.start()
    service_connection_thread.start()

    # Wait for the threads to finish
    options_menu_thread.join()
    listen_thread.join()
    service_connection_thread.join()

    print("Exiting Python program ...")
    sys.exit(SUCCESS)