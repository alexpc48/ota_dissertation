# Libraries
import sys
import socket
import selectors
import threading
import os
import types

from constants import *

# FUNCTIONS
# Function to display the options menu
def options_menu() -> int:
    print("Options:")
    print("1. Request an update")
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
                        print("Requesting update ...\n")
                    case 99: # Exit the program
                        print("Exiting ...\n")
                        break
                    case _:
                        print("Invalid option selected.\n")
        os._exit(SUCCESS)

    except KeyboardInterrupt:
        print("Exiting due to keyboard interrupt ...\n")
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
        print(f"Listening on {host}:{port} for server connections ...\n")
        listening_socket.setblocking(False)

        # Register the listening socket with the selector
        selector.register(listening_socket, selectors.EVENT_READ, data="client_listening_socket")
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
        print("Non-blocking operation could not be completed immediately. Retrying ...\n")
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
                    if key.data == "client_listening_socket":
                        _ = accept_new_connection(key.fileobj, selector)
    except Exception as e:
        print(f"An error occurred: {e}")
        os._exit(LISTENING_ERROR)

# Service the current active connections
def service_connection(selector: selectors.SelectSelector) -> int:
    try:
        while True:
            # print('servicing')
            events = selector.select(timeout=1)
            for key, mask in events:
                # Service active socket connections, not the listening socket
                if key.data != "client_listening_socket":
                    connection_socket = key.fileobj
                    # Read events
                    if mask & selectors.EVENT_READ:
                        # print('Reading')
                        recv_data = connection_socket.recv(1)
                        if recv_data:
                            print(f"Receiving data from {connection_socket.getpeername()[0]}:{connection_socket.getpeername()[1]} ...")
                            key.data.inb += recv_data
                        else:
                            print(f'Data received: {key.data.inb}')
                            selector.unregister(connection_socket)
                            # connection_socket.close() # TODO: Check if socket is open and if it is, close it
                            print(f"Connection to {connection_socket.getpeername()[0]}:{connection_socket.getpeername()[1]} closed.")
                    # Write events
                    if mask & selectors.EVENT_WRITE:
                        continue
                        # print('Writing')
    except Exception as e:
        print(f"An error occurred: {e}")
        return CONNECTION_SERVICE_ERROR
                



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
    service_connection_thread = threading.Thread(target=service_connection, daemon=False, args=(selector,))

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