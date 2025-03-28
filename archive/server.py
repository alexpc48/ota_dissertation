# Libraries
import sys
import socket
import selectors
import types
from constants import *

def accept_new_connection(socket: socket.socket) -> int:
    try:
        # Get socket information
        connection_socket, address = socket.accept()
        print(f"Accepted connection from {address}")

        connection_socket.setblocking(False)

        # Register the connection with the selector
        data = types.SimpleNamespace(address=address, inb=b"", outb=b"") # Fast way to create struct-like objects
        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        selector.register(connection_socket, events, data=data)

        return SUCCESS
    
    except Exception as e:
        print(f"An error occurred: {e}")

        # Close the connection socket if it was created
        if connection_socket in locals():
            connection_socket.close()

        return CONNECTION_ACCEPT_ERROR


def service_current_connection(key: selectors.SelectorKey, mask: int) -> int:
    try:
        socket = key.fileobj
        
        if mask & selectors.EVENT_READ: # Uses bitwise AND to check mask holds the value of EVENT_READ
            received_data = socket.recv(1024) # Recieve 1024 bytes of data
            if received_data:
                print(f"Received {received_data!r} from {key.data.address}")
                key.data.outb += received_data
                
    

# Main program
if __name__=='__main__':
    # Create a selector object
    selector = selectors.DefaultSelector()
    
    # Assign the server IP address and port
    server_host, server_port = sys.argv[1], int(sys.argv[2])
    
    # Create a listening socket
    listening_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listening_socket.bind((server_host, server_port))
    listening_socket.listen()
    print(f"Listening on {(server_host, server_port)} ...")
    listening_socket.setblocking(False)
    
    # Register the listening socket with the selector
    selector.register(listening_socket, selectors.EVENT_READ, data="listening_socket")

    # Main loop
    try:
        while True:
            # Get list of events from the selector
            events = selector.select(timeout=None) # Timeout controls how long to wait for an event before returning
            for key, mask in events:
                # If the event comes from the listening socket, accept a new connection
                if key.data == "listening_socket":
                    accept_new_connection(key.fileobj)
                # Otherwise, service the current connection
                else:
                    service_current_connection(key, mask)
    except KeyboardInterrupt:
        print("Keyboard interruption. Exiting ...")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Close connections used
        selector.close()
        listening_socket.close()
        print("Server closed.")