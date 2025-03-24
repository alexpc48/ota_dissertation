# Libraries
import socket
import selectors
import select
import types
import typing
import errno

from constants import *

# Funtion accepts new connections from clients and registers them with the selector
def accept_new_connection(socket: socket.socket, selector: selectors.SelectSelector) -> int:
    try:
        # Get socket information
        connection_socket, client_address = socket.accept()
        print(f"Accepted connection from {client_address[0]}:{client_address[1]} ...")

        connection_socket.setblocking(False)

        # Register the connection with the selector
        data = types.SimpleNamespace(address=client_address, inb=b"", outb=b"") # Fast way to create struct-like objects
        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        selector.register(connection_socket, events, data=data)

        return SUCCESS
    
    except Exception as e:
        print(f"An error occurred: {e}")

        # Close the connection socket if it was created
        if connection_socket in locals():
            connection_socket.close()

        return CONNECTION_ACCEPT_ERROR

# Function services current registered connections with their corresponding events
def service_current_connection(key: selectors.SelectorKey, mask: int, selector: selectors.SelectSelector) -> int:
    connection_socket = key.fileobj

    if mask & selectors.EVENT_READ:
        if not connection_socket.recv(1024):
            print(f"Closing connection to {key.data.address[0]}:{key.data.address[1]} ...")
            selector.unregister(connection_socket)
            connection_socket.close()

# Funtion initiates a connection to the server
def initiate_connection(host: str, port: int, selector: selectors.SelectSelector) -> typing.Tuple[socket.socket, int]:
    try:
        print(f"Initiating connection to {host}:{port} ...")
       
        connection_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connection_socket.setblocking(False)
        connection_socket.connect_ex((host, port)) # Connect to the server address

        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        data = types.SimpleNamespace(address=(host, port), inb=b"", outb=b"") # Server address
        selector.register(connection_socket, events, data=data)

        readable, writeable, _ = select.select([connection_socket], [connection_socket], [], 5) # Waits 5 seconds for the connection to be established

        if not readable or not writeable:
            print(f"Connection to {host}:{port} failed.")
            if connection_socket in locals():
                connection_socket.close()
        
            return None, CONNECTION_INITIATE_ERROR

        return connection_socket, SUCCESS
    
    except Exception as e:
        print(f"An error occurred: {e}")
                
        # Close the connection socket if it was created
        if connection_socket in locals():
            connection_socket.close()
        
        return None, CONNECTION_INITIATE_ERROR

# Function closes the connection to the server
def close_connection(connection_socket: socket.socket, selector: selectors.SelectSelector) -> int:
    try:
        print(f"Closing connection to {connection_socket.getpeername()[0]}:{connection_socket.getpeername()[1]}...")

        selector.unregister(connection_socket)
        connection_socket.close()
    
    except Exception as e:
        print(f"An error occurred: {e}")

        return CONNECTION_CLOSE_ERROR