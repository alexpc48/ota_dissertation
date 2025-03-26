# Libraries
import socket
import selectors
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
        return CONNECTION_ACCEPT_ERROR

# Funtion initiates a connection to the server
def initiate_connection(host: str, port: int, messages: list, selector: selectors.SelectSelector) -> typing.Tuple[socket.socket, int]:
    try:
        print(f"Initiating connection to {host}:{port} ...")
       
        connection_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connection_socket.setblocking(False)
        connection_socket.connect_ex((host, port)) # Connect to the server address
        msg_total = sum(len(message) for message in messages)
        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        data = types.SimpleNamespace(address=(host, port), inb=b"", outb=b"", msg_total=msg_total, recv_total=0, messages=messages.copy(), connected=False) # Server address
        selector.register(connection_socket, events, data=data)

        # *** Written with the help of AI ***
        # Wait for the connection to complete (blocks all other operations)
        while not data.connected:
            events = selector.select(timeout=5)  # Wait 5 seconds until timeout
            for key, mask in events:
                if mask & selectors.EVENT_WRITE:
                    # Check if the connection was successful
                    err = connection_socket.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
                    if err == 0:
                        print(f"Connection to {host}:{port} successful.")
                        data.connected = True
                        return connection_socket, SUCCESS
                    else:
                        print(f"Connection to {host}:{port} failed with error: {errno.errorcode[err]}")
                        selector.unregister(connection_socket)
                        return None, CONNECTION_INITIATE_ERROR

        return connection_socket, SUCCESS
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return None, CONNECTION_INITIATE_ERROR

# Function closes the connection to the server
def close_connection(connection_socket: socket.socket, selector: selectors.SelectSelector) -> int:

    try:
        print(f"Closing connection to {connection_socket.getpeername()[0]}:{connection_socket.getpeername()[1]}...")
        
        selector.unregister(connection_socket)
        connection_socket.close()
        
        return SUCCESS
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return CONNECTION_CLOSE_ERROR
    
# Function services current registered connections with their corresponding events
def service_current_connection(key: selectors.SelectorKey, mask: int, selector: selectors.SelectSelector) -> int:
    try:
        connection_socket = key.fileobj

        # Service events
        if mask & selectors.EVENT_READ:
            received_data = connection_socket.recv(1024)
            if received_data:
                print (f"Received data from {connection_socket.getpeername()[0]}:{connection_socket.getpeername()[1]} ...")
                key.data.outb += received_data
            else:
                return close_connection(connection_socket, selector)
        if mask & selectors.EVENT_WRITE:
            if key.data.outb:
                print(f"Echoing {key.data.outb!r} to {key.data.address}")
                sent = connection_socket.send(key.data.outb)  # Should be ready to write
                key.data.outb = key.data.outb[sent:]

    except Exception as e:
        print(f"An error occurred: {e}")
        return CONNECTION_SERVICE_ERROR