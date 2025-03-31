# HEADER FILE

# Libraries
import selectors
import os
from constants import *
from server_functions import *

def menu_thread(selector: selectors.SelectSelector, response_event: threading.Event, response_data: dict) -> None:
    try:
        while True:
            option = options_menu()
            match option:
            
                case '1': # Push the latest update to the client
                    print("Pushing the latest update to the client ...")
                    ret_val = push_update(selector, response_event, response_data)
                    if ret_val == SUCCESS:
                        print("Update pushed successfully.")
                    elif ret_val == CLIENT_NOT_UPDATE_READY_ERROR:
                        print("Error: Client is not ready to receive the update.")
                    elif ret_val == CONNECTION_INITIATE_ERROR:
                        print("Error: Connection initiation failed.")
                    else:
                        print("An error occurred while pushing the update.")
                        print("Please check the logs for more details.")

                case '98': # Redisplay the options menu
                    continue

                case '99': # Exit the program
                    print("Exiting ...")
                    # TODO: Implement proper graceful exit
                    os._exit(SUCCESS)

                case _:
                    print(f"Invalid option '{option}' entered.")

    except KeyboardInterrupt:
        print("Exiting due to keyboard interrupt ...")
        os._exit(KEYBOARD_INTERRUPT)

    except Exception as e:
        print(f"An error occurred: {e}")
        # TODO: Implement proper graceful exit
        os._exit(ERROR)

def listen(selector: selectors.SelectSelector) -> None:
    try:
        while True:
            # Get list of events from the selector
            timeout_interval = random.randint(1, 10)
            events = selector.select(timeout=timeout_interval) # Refreshes in random intervals to avoid collisions
            if events:
                for key, _ in events:
                    # If the event comes from the listening socket, accept the new connection
                    if key.data == "listening_socket":
                        ret_val = accept_new_connection(key.fileobj, selector)
                        if ret_val == SUCCESS:
                            print("New connection accepted.")
                        elif ret_val == CONNECTION_ACCEPT_ERROR:
                            print("Error: Failed to accept new connection.")
                        else:
                            print("An error occurred while accepting the connection.")
                            print("Please check the logs for more details.")

    except Exception as e:
        print(f"An error occurred: {e}")
        # TODO: Implement proper graceful exit
        os._exit(LISTENING_ERROR)

def service_connection(selector: selectors.SelectSelector, response_event: threading.Event, response_data: dict) -> int:
    try:
        while True:
            # Get list of events from the selector
            timeout_interval = random.randint(1, 10)
            events = selector.select(timeout=timeout_interval) # Refreshes in random intervals to avoid collisions
            for key, mask in events:
                # Service active socket connections, not the listening socket
                if key.data == "listening_socket":
                    continue

                connection_socket = key.fileobj
                remote_host, remote_port = connection_socket.getpeername()[0], connection_socket.getpeername()[1]

                # Read events
                if mask & selectors.EVENT_READ:
                    # Read all the data at once that comes in from the socket
                    while True:
                        recv_data = connection_socket.recv(BYTES_TO_READ)
                        print(f"Receiving data from {remote_host}:{remote_port} in {BYTES_TO_READ} byte chunks...")
                        key.data.inb += recv_data

                        if not recv_data or EOF_BYTE in recv_data:
                            print(f"Data {key.data.inb} from {remote_host}:{remote_port} received.")
                            break

                    if not recv_data or EOF_BYTE in recv_data:

                        if key.data.inb.startswith(UPDATE_CHECK_REQUEST):
                            print("Update check request received.")
                            print("Checking for new updates ...")
                            update_available, update_available_bytes, _ = check_for_updates()
                            if update_available == True:
                                print("New update available.")
                                key.data.outb = update_available_bytes # Send back result from the update check request
                            elif update_available == False:
                                print("No new updates available.")
                                key.data.outb = update_available_bytes

                        elif key.data.inb.startswith(FILE_RECEIVED_ACK):
                            print("The files was received by the client.")

                        elif key.data.inb.startswith(UPDATE_DOWNLOAD_REQUEST):
                            print("Update download request received.")
                            file_data, _ = get_update_file()
                            key.data.outb = file_data

                        elif key.data.inb.startswith(UPDATE_READY):
                            print("The client is ready to receive the update.")
                            response_data["update_readiness"] = True
                            file_data, _ = get_update_file()
                            key.data.outb = file_data

                        elif key.data.inb.startswith(UPDATE_NOT_READY):
                            print("The client is not ready to receive the update.")
                            response_data["update_readiness"] = False

                        elif key.data.inb.startswith(b''):
                            print(f"No data received from {remote_host}:{remote_port}.")

                        key.data.inb = b''  # Clear the input buffer
                    
                    # If connection has no data to send and the server has nothing to send, close the connection
                    if (not recv_data or EOF_BYTE in recv_data) and not key.data.outb:
                        _ = close_connection(connection_socket, selector)
                        response_event.set() # Set completion flag for the connection

                # Write events
                if mask & selectors.EVENT_WRITE:
                    if key.data.outb:
                        print(f"Sending data {key.data.outb} to {remote_host}:{remote_port} ...")
                        key.data.outb += EOF_BYTE # Add end of file tag to the data to be sent
                        while key.data.outb:
                            sent = connection_socket.send(key.data.outb)
                            key.data.outb = key.data.outb[sent:]
                        print("Data sent.")

    except Exception as e:
        print(f"An error occurred: {e}")
        # Doesn't need to exit program, just return error code
        _ = close_connection(connection_socket, selector)
        return CONNECTION_SERVICE_ERROR