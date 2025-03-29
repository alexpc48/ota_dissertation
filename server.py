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
    print("1. Push an update to the client")
    print("-------------------------------------------------------------------------------------------")
    print("10. Get the client update readiness status") # TODO
    print("11. Get the client update status") # Check if the update has been installed, failed, behind, etc. TODO
    print("12. Get the client update version") # TODO
    print("-------------------------------------------------------------------------------------------")
    print("20. Change the update file")
    print("-------------------------------------------------------------------------------------------")
    print("98. Redisplay the options menu")
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
                        print("Pushing update ...")
                        ret_val = push_update()
                        if ret_val == CLIENT_NOT_UPDATE_READY_ERROR:
                            print("Error: Client is not ready to receive the update.")
                        elif ret_val == CONNECTION_INITIATE_ERROR:
                            print("Error: Connection initiation failed.")
                    case '98': # Redisplay the options menu
                        continue
                    case '99': # Exit the program
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
def push_update() -> int:
    try:
        
        db_connection = sqlite3.connect('server_ota_updates.db')
        cursor = db_connection.cursor()
        query_result = (cursor.execute("SELECT vehicles_entry_id, vehicle_id, vehicle_ip, vehicle_port FROM vehicles ORDER BY vehicles_entry_id")).fetchall()
        db_connection.close()

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

        print(f"Initiating connection to {client_host}:{client_port} ...")

        connection_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connection_socket.setblocking(False)

        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        data = types.SimpleNamespace(address=(client_host, client_port), inb=b"", outb=b"", connected=False)
        
        # Wait for the connection to complete (blocks all other operations)
        connection_attempts = 0
        while not data.connected:
            err = connection_socket.connect_ex((client_host, client_port)) # Try connecting to the client
            print('[SYN] sent')
            if err == 10056: # Connection made
                print(f"Connection to {client_host}:{client_port} successful.")
                data.connected = True
                print('[SYN-ACK] received')
                break
            elif err == 10035:
                print(f"Connection to {client_host}:{client_port} in progress ...")
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
                print(f"Connection to {client_host}:{client_port} failed with error: {errno.errorcode[err]}\n")
                print("Please check the client IP and port.")
                return CONNECTION_INITIATE_ERROR

        # Register the connection with the selector for read and write events
        selector.register(connection_socket, events, data=data)


        print('Preparing data to send ...')
        data.outb = UPDATE_READINESS_REQUEST
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
    database = None
    local_host, local_port = sys.argv[1], int(sys.argv[2])
    
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