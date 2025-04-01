# HEADER FILE

# Libraries
import selectors
import os
import random
import re
from constants import *
from client_functions import *

# (Use of AI) Thread for displaying the options menu in a non-blocking way
def menu_thread(selector: selectors.SelectSelector, response_event: threading.Event, response_data: dict) -> None:
    try:
        while True:
            option = options_menu()
            match option:

                case '1': # Request update check from the server
                    print("Checking the server for updates ...")
                    _, ret_val = check_for_update(selector, response_event, response_data)
                    if ret_val == SUCCESS:
                        print("There is a new update.")
                    elif ret_val == NO_UPDATE_ERROR:
                        print("Error: There is no new udpate.")
                    elif ret_val == CONNECTION_INITIATE_ERROR:
                        print("Error: Connection initiation failed.")
                    else:
                        print("An error occurred.")
                        print("Please check the logs for more details.")

                case '2': # Download updates from the server
                    print("Downloading updates from the server ...")
                    ret_val = download_update(selector, response_event, response_data)
                    if ret_val == SUCCESS:
                        print("Update downloaded successfully.")
                    elif ret_val == UPDATE_NOT_AVALIABLE:
                        print("Error: No updates available to download.")
                    elif ret_val == CLIENT_NOT_UPDATE_READY_ERROR:
                        print("Error: Client is not ready to receive the update.")
                    elif ret_val == QUEUED_UPDATE_ERROR:
                        print("Error: There is an update already queued for install.")
                    else:
                        print("An error occurred.")
                        print("Please check the logs for more details.")

                case '3': # Install the update
                    print("Installing the update ...")
                    ret_val = install_update()
                    if ret_val == SUCCESS:
                        print("Update installed successfully.")
                    elif ret_val == CLIENT_NOT_UPDATE_READY_ERROR:
                        print("Error: Client is not ready to receive the update.")
                    elif ret_val == UPDATE_NOT_AVALIABLE_ERROR:
                        print("Error: There is no update queued for install.")
                    elif ret_val == UPDATE_INSTALL_ERROR:
                        print("Error: There was an error installing the udpate.")
                    else:
                        print("An error occurred.")
                        print("Please check the logs for more details.")

                case '10': # Change the update readiness status
                    print("Changing the update readiness status ...")
                    ret_val = change_update_readiness()
                    if ret_val == SUCCESS:
                        print("Update readiness status changed successfully.")
                    elif ret_val == UPDATE_STATUS_REPEAT_ERROR:
                        print("Error: Update readiness status is already set to the same value.")
                    else:
                        print("An error occured.")
                        print("Please check the logs for more details.")

                case '20': # Check the update readiness
                    print("Displaying the update readiness status ...")
                    update_readiness_status, _, ret_val = check_update_readiness_status()
                    if ret_val == SUCCESS:
                        print("Update readiness status checked successfully.")
                        print(f"Update readiness status: {update_readiness_status}")
                    else:
                        print("An error occured.")
                        print("Please check the logs for more details.")

                case '21':
                    print("Displaying the update version ...")
                    update_version, ret_val = get_update_version()
                    if ret_val == SUCCESS:
                        print(f"Update version: {update_version}")
                        print("Update version checked successfully.")
                    else:
                        print("An error occured.")
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

def service_connection(selector: selectors.SelectSelector, response_event: threading.Event, response_data: dict,) -> int:
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
                    while True:
                        recv_data = connection_socket.recv(BYTES_TO_READ)
                        print(f"Receiving data from {remote_host}:{remote_port} in {BYTES_TO_READ} byte chunks...")
                        key.data.inb += recv_data

                        if not recv_data or EOF_BYTE in recv_data:
                            print(f"Data {key.data.inb} from {remote_host}:{remote_port} received.")
                            break

                    if not recv_data or EOF_BYTE in recv_data:

                        if key.data.inb.startswith(UPDATE_AVALIABLE):
                            print("There is an update available.")
                            response_data["update_available"] = True
                            
                        elif key.data.inb.startswith(UPDATE_NOT_AVALIABLE):
                            print("There is no update available.")
                            response_data["update_available"] = False

                        elif key.data.inb.startswith(UPDATE_READINESS_REQUEST):
                            print("Update readiness request received.")
                            update_readiness, update_readiness_bytes, _ = check_update_readiness_status()
                            if update_readiness == True:
                                print("Client is ready to receive the update.")
                                key.data.outb = update_readiness_bytes
                            elif update_readiness == False:
                                print("Client is not ready to receive the update.")
                                key.data.outb = update_readiness_bytes

                        elif key.data.inb.startswith(UPDATE_READINESS_STATUS_REQUEST):
                            print("Update readiness request received.")
                            update_readiness, update_readiness_bytes, _ = check_update_readiness_status()
                            if update_readiness == True:
                                print("Client is ready to receive the update.")
                                key.data.outb = update_readiness_bytes + REQUEST
                            elif update_readiness == False:
                                print("Client is not ready to receive the update.")
                                key.data.outb = update_readiness_bytes + REQUEST

                        # FIXME: The way this is done is bad since it could result in the bytes from RECEIVED_FILE_CHECK_REQUEST being in the middle of the data stream
                        # and not at the end, which could mean that even if no all the data was sent and there was an error, the client might still think the download was successfull.
                        # Currently uses 256 bytes of random data as EOF_BYTE to counteract possibility of collisions.
                        # FIXME: Should use header file for meta data transfer.
                        elif (EOF_TAG_BYTE + RECEIVED_FILE_CHECK_REQUEST) in key.data.inb:
                            # AI used for pattern matching code
                            # Gets the header section data from the received data
                            pattern = rb'^(.*?)' + re.escape(FILE_HEADER_SECTION_END)
                            header = re.match(pattern, key.data.inb)
                            prefix = header.group(0)
                            update_file_name = (header.group(1)).decode()

                            suffix = EOF_TAG_BYTE + RECEIVED_FILE_CHECK_REQUEST + EOF_BYTE
                            file_data = key.data.inb.removeprefix(prefix) # Remove header bytes
                            file_data = file_data.removesuffix(suffix) # Remove end of file bytes
                            
                            ret_val = write_update_file_to_database(update_file_name, file_data)
                            if ret_val == SUCCESS:
                                print("Update file written to database successfully.")
                            elif ret_val == DOWNLOAD_UPDATE_ERROR:
                                print("Error: Failed to write update file to database.")
                                return DOWNLOAD_UPDATE_ERROR
                            else:
                                print("An error occurred while retrieving the database name.")
                                print("Please check the logs for more details.")
                                return ERROR

                            print("File receive check request received.")
                            print("Sending confirmation to server ...")
                            key.data.outb = FILE_RECEIVED_ACK

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