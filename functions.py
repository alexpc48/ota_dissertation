import selectors
import socket

from constants import *

def check_for_update() -> int:
    update_available = True
    update_available_bytes = UPDATE_AVALIABLE
    return update_available, update_available_bytes, SUCCESS

# Service the current active connections (shared function with server and client - TODO: Needs seperating)
def service_connection(selector: selectors.SelectSelector) -> int:
    try:
        while True:
            events = selector.select(timeout=1)
            for key, mask in events:
                # Service active socket connections, not the listening socket
                if key.data == "listening_socket":
                    continue
                connection_socket = key.fileobj
                remote_host, remote_port = connection_socket.getpeername()[0], connection_socket.getpeername()[1]
                # Read events
                if mask & selectors.EVENT_READ:
                    while True:
                        recv_data = connection_socket.recv(BYTES_TO_READ)
                        print(f"Receiving data from {remote_host}:{remote_port} in {BYTES_TO_READ} byte chunks...")
                        if not recv_data or recv_data == EOF_BYTE:
                            print(f"Data {key.data.inb} from {remote_host}:{remote_port} received.")
                            break
                        key.data.inb += recv_data

                    if not recv_data or recv_data == EOF_BYTE:
                        if key.data.inb == UPDATE_CHECK_REQUEST:
                            print("Update check request received.\nChecking for updates ...")
                            update_available, update_available_bytes, _ = check_for_update()
                            if update_available:
                                print("Update available.")
                                key.data.outb = update_available_bytes
                            else:
                                print("No updates available.")
                                key.data.outb = update_available_bytes
                        elif key.data.inb == UPDATE_DOWNLOAD_REQUEST:
                            print("Update download request received.\nDownloading update ...")
                            # TODO: Do soemthing to download and sent the update
                        elif key.data.inb == b'':
                            print(f"No data received from {remote_host}:{remote_port}.")
                        elif key.data.inb == UPDATE_AVALIABLE:
                            print("Update available message received.")
                        elif key.data.inb == UPDATE_NOT_AVALIABLE:
                            print("No update available message received.")
                        else:
                            print("Invalid request code or update has been received.")
                        key.data.inb = b''  # Clear the input buffer

                    if (not recv_data or recv_data == EOF_BYTE) and not key.data.outb: # If connection has no data to send and the server has nothing to send, close the connection
                        selector.unregister(connection_socket)
                        print('Socket unregistered from the selector.')
                        connection_socket.close()
                        print(f'Connection with {remote_host}:{remote_port} closed.')
                # Write events
                if mask & selectors.EVENT_WRITE:
                    if key.data.outb:
                        print(f"Sending data to {remote_host}:{remote_port} ...")
                        key.data.outb += EOF_BYTE
                        while key.data.outb:
                            sent = connection_socket.send(key.data.outb)
                            key.data.outb = key.data.outb[sent:]
                        print("Data sent.")

    except Exception as e:
        print(f"An error occurred: {e}")
        return CONNECTION_SERVICE_ERROR