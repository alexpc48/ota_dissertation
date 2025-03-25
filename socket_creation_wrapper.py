# Libraries
import socket
import selectors

from constants import *


# Create an IPv4 listening socket
def create_listening_socket(host: str, port: int, selector: selectors.SelectSelector) -> int:
    try:
        listening_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listening_socket.bind((host, port))
        listening_socket.listen()
        print(f"Listening on {host}:{port} ...")
        listening_socket.setblocking(False)

        # Register the listening socket with the selector
        selector.register(listening_socket, selectors.EVENT_READ, data="listening_socket")

        return SUCCESS
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return LISTENING_SOCKET_CREATION_ERROR