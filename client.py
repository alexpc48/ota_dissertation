# Libraries
import sys
import socket
import selectors
import threading
import os
import types
import errno

from constants import *
from functions import *

# FUNCTIONS
# Function to display the options menu
def options_menu() -> int:
    print("Options:")
    print("1. Check for an update") # Checks the server for an update it
    print("2. Download updates") # Downloads the updates from the server

    print("10. Change the update readiness status") # Changes the update readiness status

    print("20. Display the update readiness status") # Displays the current update readiness status
    print("21. Display the update version") # Displays the current update version
    print("98. Redisplay the options menu") # Redisplays the options menu

    print("99. Exit")
    return int(input("Enter an option: "))

# (Use of AI) Thread for displaying the options menu in a non-blocking way
def menu_thread() -> None:
    try:
        while True:
            option = options_menu()
            if option:
                match option:
                    case 1: # Request update from the server
                        print("Checking for updates ...")
                        _, _ = check_for_update(server_host, server_port)
                    case 2: # Download updates from the server
                        print("Downloading updates ...")
                        ret_val = download_update(server_host, server_port)
                        if ret_val == UPDATE_NOT_AVALIABLE:
                            print("No updates available to download.")
                    case 98: # Redisplay the options menu
                        continue
                    case 99: # Exit the program
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
        connection_socket.connect_ex((server_host, server_port))
        print('[SYN] sent')

        # Register the connection with the selector for read and write events
        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        data = types.SimpleNamespace(address=(server_host, server_port), inb=b"", outb=b"", connected=False)
        selector.register(connection_socket, events, data=data)

        # *** Written with the help of AI ***
        # Wait for the connection to complete (blocks all other operations)
        while not data.connected:
            # FIXME: Timeout doesnt work
            # The program errors and doenst work even when the client does come up
            # Not urgent for now (out of scope) but does need fixing
            events = selector.select(timeout=10)
            for _, mask in events:
                # Check for write event (TCP socket enters write event after successfull connection)
                if mask & selectors.EVENT_WRITE:
                    err = connection_socket.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
                    if err == 0:
                        print(f"Connection to {server_host}:{server_port} successful.")
                        data.connected = True
                        print('[SYN-ACK] received')
                        break
                    else:
                        print(f"Connection to {server_host}:{server_port} failed with error: {errno.errorcode[err]}")
                        selector.unregister(connection_socket)
                        return CONNECTION_INITIATE_ERROR
                    
        print('Preparing data to send ...')
        data.outb = UPDATE_CHECK_REQUEST
        print('Data ready to send.')

        # Wait for the response to be processed by service_connection
        response_event.clear()
        response_event.wait(timeout=10)  # Wait for up to 10 seconds
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
def download_update(server_host: str, server_port: int) -> int:
    update_available, _ = check_for_update(server_host, server_port)
    if not update_available:
        print("No update available to download.")
        return UPDATE_NOT_AVALIABLE
    
    try:
        print(f"Initiating connection to {server_host}:{server_port} ...")

        connection_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connection_socket.setblocking(False)
        connection_socket.connect_ex((server_host, server_port))
        print('[SYN] sent')

        # Register the connection with the selector for read and write events
        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        data = types.SimpleNamespace(address=(server_host, server_port), inb=b"", outb=b"", connected=False)
        selector.register(connection_socket, events, data=data)

        # *** Written with the help of AI ***
        # Wait for the connection to complete (blocks all other operations)
        while not data.connected:
            # FIXME: Timeout doesnt work
            # The program errors and doenst work even when the client does come up
            # Not urgent for now (out of scope) but does need fixing
            events = selector.select(timeout=1)
            for _, mask in events:
                # Check for write event (TCP socket enters write event after successfull connection)
                if mask & selectors.EVENT_WRITE:
                    err = connection_socket.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
                    if err == 0:
                        print(f"Connection to {server_host}:{server_port} successful.")
                        data.connected = True
                        print('[SYN-ACK] received')
                        break
                    else:
                        print(f"Connection to {server_host}:{server_port} failed with error: {errno.errorcode[err]}")
                        selector.unregister(connection_socket)
                        return CONNECTION_INITIATE_ERROR
                    
        print('Preparing data to send ...')
        data.outb = UPDATE_DOWNLOAD_REQUEST
        print('Data ready to send.')

        # Wait for the response to be processed by service_connection
        response_event.clear()
        response_event.wait(timeout=10)  # Wait for up to 10 seconds
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
    if len(sys.argv) != 5:
        print("Usage: python3 client.py <local_host> <local_port> <server_host> <server_port>")
        sys.exit(ERROR)

    # Create a selector object
    selector = selectors.DefaultSelector()

    # Assign variables from arguments
    local_host, local_port, server_host, server_port = sys.argv[1], int(sys.argv[2]), sys.argv[3], int(sys.argv[4])
    
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
    service_connection_thread = threading.Thread(target=service_connection, daemon=False, args=(selector, response_event, response_data))

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