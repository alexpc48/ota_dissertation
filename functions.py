# HEADER FILE
# Common functions for both the server and client

# Libraries
import socket
import selectors
import types
import typing
import errno
import random
import time
from constants import *

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
            elif err == 10035 or err == errno.EINPROGRESS: # Non-blocking connection in progress
                print(f"Connection to {host}:{port} in progress ...")
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