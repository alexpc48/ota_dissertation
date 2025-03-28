# Libraries
import sys
import socket
import selectors
import threading
import os
import types
import errno
import typing

from constants import *
from functions import *

# FUNCTIONS
# Function to display the options menu
def options_menu() -> int:
    print("Options:")
    print("1. Push and update")
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
                        print("Pushing update ...")
                        push_update(client_host, client_port)
                    case 99: # Exit the program
                        print("Exiting ...")
                        break
                    case _:
                        print("Invalid option selected.")
        os._exit(SUCCESS)
    except Exception as e:
        print(f"An error occurred: {e}")
        os._exit(ERROR)

# Function to create a listening socket for the server to connect to
def create_listening_socket(host: str, port: int, selector: selectors.SelectSelector) -> int:
    try:
        listening_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listening_socket.bind((host, port))
        listening_socket.listen()
        print(f"Listening on {host}:{port} for client connections ...")
        listening_socket.setblocking(True)

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
        print(f"\nAccepted connection from {address[0]}:{address[1]} ...")
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
                        accept_new_connection(key.fileobj, selector)
    except Exception as e:
        print(f"An error occurred: {e}")
        os._exit(LISTENING_ERROR)

# Function to push an update to the client
def push_update(client_host: str, client_port: int) -> int:
    try:
        print(f"Initiating connection to {client_host}:{client_port} ...")

        connection_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connection_socket.setblocking(False)
        connection_socket.connect_ex((client_host, client_port))
        print('[SYN] sent')

        # Register the connection with the selector for read and write events
        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        data = types.SimpleNamespace(address=(client_host, client_port), inb=b"", outb=b"", connected=False)
        selector.register(connection_socket, events, data=data)

        # *** Written with the help of AI ***
        # Wait for the connection to complete (blocks all other operations)
        while not data.connected:
            events = selector.select(timeout=10)  # Wait 10 seconds until timeout of connection
            for key, mask in events:
                # Check for write event (TCP socket enters write event after successfull connection)
                if mask & selectors.EVENT_WRITE:
                    err = connection_socket.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
                    if err == 0:
                        print(f"Connection to {client_host}:{client_port} successful.")
                        data.connected = True
                        print('[SYN-ACK] received')
                        break
                    else:
                        print(f"Connection to {client_host}:{client_port} failed with error: {errno.errorcode[err]}\n")
                        selector.unregister(connection_socket)
                        return CONNECTION_INITIATE_ERROR
                    
        print('Preparing data to send ...')
        data.outb, _ = get_update_file()
        print('Data ready to send.')

        # TODO: Just sends the data and doesnt check if the client can receive it yet.
        # Need to add check to ask client if they can receive the data or not, and if not then check back later to see if they are.

        # Wait for the response to be processed by service_connection
        response_event.clear()
        response_event.wait(timeout=10)  # Wait for up to 10 seconds
        if not response_event.is_set():
            print("Timeout waiting for server response.")
            return CONNECTION_SERVICE_ERROR
        
        print("Pushed update successfully.")
        return SUCCESS
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return CONNECTION_INITIATE_ERROR










# Main program
if __name__=='__main__':
    # Usage
    if len(sys.argv) != 5:
        print("Usage: python3 server.py <local_host> <local_port> <client_host> <client_port>")
        sys.exit(ERROR)

    # Create a selector object
    selector = selectors.DefaultSelector()

    # Assign variables from arguments
    local_host, local_port, client_host, client_port = sys.argv[1], int(sys.argv[2]), sys.argv[3], int(sys.argv[4])
    
    # Create listening socket so that the server can connect forcefully (i.e, push updates to client)
    ret_val = create_listening_socket(local_host, local_port, selector)
    if ret_val != SUCCESS:
        print('Failed to create listening socket')
        sys.exit(ret_val)

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