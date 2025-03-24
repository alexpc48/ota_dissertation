# Libraries
import sys
import socket
import selectors
import types
from constants import *
import time
import typing

# Functions
# Funtion initiates a connection to the server
def initiate_connection(host: str, port: int) -> typing.Tuple[socket.socket, int]:
    try:
        print(f"Initiating connection to {host}:{port} ...")
       
        connection_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connection_socket.setblocking(False)
        connection_socket.connect_ex((host, port)) # Connect to the server address
        
        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        data = types.SimpleNamespace(address=(host, port), inb=b"", outb=b"") # Server address
        selector.register(connection_socket, events, data=data)

        return connection_socket, SUCCESS
    
    except Exception as e:
        print(f"An error occurred: {e}")
                
        # Close the connection socket if it was created
        if connection_socket in locals():
            connection_socket.close()
        
        return CONNECTION_INITIATE_ERROR

# Function closes the connection to the server
def close_connection(connection_socket):
    try:
        print(f"Closing connection ...")

        selector.unregister(connection_socket)
        connection_socket.close()
    
    except Exception as e:
        print(f"An error occurred: {e}")

        return CONNECTION_CLOSE_ERROR

# Main program
if __name__=='__main__':
    # Create a selector object
    selector = selectors.DefaultSelector()
    
    # Assign the server IP address and port
    server_host, server_port = sys.argv[1], int(sys.argv[2])
    
    while True:
        # Initiate a connection to the server
        connection_socket, _ = initiate_connection(server_host, server_port)
        
        time.sleep(5)

        close_connection(connection_socket)

        time.sleep(5)