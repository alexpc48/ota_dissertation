import selectors
import threading
import typing

from constants import *

# Check if there is an update
# TODO: Implement properly
def check_for_update() -> int:
    update_available = True
    update_available_bytes = UPDATE_AVALIABLE
    return update_available, update_available_bytes, SUCCESS

# Get update file
def get_update_file() -> typing.Tuple[bytes, int]:
    with open('snoopy.png', 'rb') as file:
        file_data = file.read()
    # print(file_data)
    return file_data, SUCCESS

# Client checks if it is ready to receive the update
def check_update_readiness(update_readiness: bool) -> int:
    if update_readiness == True:
        update_readiness_bytes = UPDATE_READY
    elif update_readiness == False:
        update_readiness_bytes = UPDATE_NOT_READY
    return update_readiness, update_readiness_bytes, SUCCESS

# Service the current active connections (shared function with server and client - TODO: Needs seperating)
def service_connection(selector: selectors.SelectSelector, response_event: threading.Event, response_data: dict) -> int:
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
                        # print(recv_data)
                        print(f"Receiving data from {remote_host}:{remote_port} in {BYTES_TO_READ} byte chunks...")
                        key.data.inb += recv_data
                        if not recv_data or EOF_BYTE in recv_data:
                            print(f"Data {key.data.inb} from {remote_host}:{remote_port} received.")
                            break

                    if not recv_data or EOF_BYTE in recv_data:

                        # Server
                        if key.data.inb.startswith(UPDATE_CHECK_REQUEST):
                            print("Update check request received.\nChecking for updates ...")
                            update_available, update_available_bytes, _ = check_for_update()
                            if update_available:
                                print("Update available for client.")
                                key.data.outb = update_available_bytes
                            else:
                                print("No updates available for client.")
                                key.data.outb = update_available_bytes

                        # Server
                        elif key.data.inb.startswith(UPDATE_DOWNLOAD_REQUEST):
                            print("Update download request received.\nSending update ...")
                            update_file, _ = get_update_file()
                            key.data.outb = update_file + EOF_TAG_BYTE + RECEIVED_FILE_CHECK_REQUEST

                        # Server
                        elif key.data.inb.startswith(FILE_RECEIVED):
                            print("File received by the client.")
                        
                        # Server
                        elif key.data.inb.startswith(UPDATE_READY):
                            print("Client is ready to receive the update.")
                            response_data["update_readiness"] = True
                            print("Preparing update file ...")
                            update_file, _ = get_update_file()
                            key.data.outb = update_file + EOF_TAG_BYTE + RECEIVED_FILE_CHECK_REQUEST

                        # Server
                        elif key.data.inb.startswith(UPDATE_NOT_READY):
                            print("Client is not ready to receive the update.")
                            response_data["update_readiness"] = False

                        #Client
                        elif key.data.inb.startswith(UPDATE_AVALIABLE):
                            print("There is an update available.")
                            response_data["update_available"] = True
                            
                        # Client
                        elif key.data.inb.startswith(UPDATE_NOT_AVALIABLE):
                            print("There is no update available.")
                            response_data["update_available"] = False

                        # Client
                        elif key.data.inb.startswith(UPDATE_READINESS_REQUEST):
                            print("Update readiness request received.")
                            update_readiness, update_readiness_bytes, _ = check_update_readiness(key.data.update_readiness)
                            if update_readiness:
                                print("Client is ready to receive the update.")
                                key.data.outb = update_readiness_bytes
                            else:
                                print("Client is not ready to receive the update.")
                                key.data.outb = update_readiness_bytes

                        # Client
                        # FIXME: The way this is done is bad since it could result in the bytes from RECEIVED_FILE_CHECK_REQUEST being in the middle of the data stream
                        # and not at the end, which could mean that even if no all the data was sent and there was an error, the client might still think the download was successfull.
                        elif (EOF_TAG_BYTE + RECEIVED_FILE_CHECK_REQUEST) in key.data.inb:
                            print(key.data.inb)
                            suffix = EOF_TAG_BYTE + RECEIVED_FILE_CHECK_REQUEST + EOF_BYTE
                            file_data = key.data.inb.removesuffix(suffix) # Remove end of file bytes
                            print(f"File data: {file_data}")
                            new_file_name = 'file..png'
                            with open(new_file_name, 'wb') as file:
                                file.write(file_data)
                            print(f"File reconstructed and written to {new_file_name}.")
                            print("File receive check request received.")
                            print("Sending confirmation to server ...")
                            key.data.outb = FILE_RECEIVED

                        # Server and client
                        elif key.data.inb.startswith(b''):
                            print(f"No data received from {remote_host}:{remote_port}.")
                        else:
                            print("ELSE")

                        key.data.inb = b''  # Clear the input buffer

                    if (not recv_data or EOF_BYTE in recv_data) and not key.data.outb: # If connection has no data to send and the server has nothing to send, close the connection
                        selector.unregister(connection_socket)
                        print('Socket unregistered from the selector.')
                        connection_socket.close()
                        print(f'Connection with {remote_host}:{remote_port} closed.')
                        response_event.set() # Set completion flag for the connection
                # Write events
                if mask & selectors.EVENT_WRITE:
                    if key.data.outb:
                        print(f"Sending data {key.data.outb} to {remote_host}:{remote_port} ...")
                        key.data.outb += EOF_BYTE
                        while key.data.outb:
                            sent = connection_socket.send(key.data.outb)
                            key.data.outb = key.data.outb[sent:]
                        # print(key.data.outb)
                        print("Data sent.")

    except Exception as e:
        print(f"An error occurred: {e}")
        return CONNECTION_SERVICE_ERROR