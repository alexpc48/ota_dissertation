# Libraries
import socket
import selectors

from constants import *


# Create an IPv4 listening socket
def create_listening_socket(host: str, port: int, selector: selectors.SelectSelector) -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((host, port))
    sock.listen()
    print(f"Listening on {host}:{port} ...")
    sock.setblocking(False)

    # Register the listening socket with the selector
    selector.register(sock, selectors.EVENT_READ, data="listening_socket")

    return SUCCESS