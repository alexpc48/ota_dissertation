# HEADER FILE

# Libraries
import selectors
import os
import re
import struct
import constants
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
                        print("An error occurred.")
                        print("Please check the logs for more details.")
                
                case '10': # Check client for update readiness status
                    print("Checking client for update readiness status ...")
                    update_readiness, ret_val = get_client_update_readiness_status(selector, response_event, response_data)
                    if ret_val == SUCCESS and update_readiness == True:
                        print("Client currently is ready to install updates.")
                    elif ret_val == CLIENT_NOT_UPDATE_READY_ERROR and update_readiness == False:
                        print("Error: Client is not ready to receive the update.")
                    elif ret_val == CONNECTION_INITIATE_ERROR:
                        print("Error: Connection initiation failed.")
                    else:
                        print("An error occurred.")
                        print("Please check the logs for more details.")
                
                case '12': # Get the clients current update version
                    print("Getting the clients current update version ...")
                    ret_val = get_client_update_version(selector, response_event, response_data)
                    if ret_val == SUCCESS:
                        print("Client update version retrieved successfully.")
                    elif ret_val == CONNECTION_INITIATE_ERROR:
                        print("Error: Connection initiation failed.")
                    else:
                        print("An error occurred.")
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
                            print("An error occurred.")
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
                # AI assistance used for creating custom header for the packet

                # Service active socket connections, not the listening socket
                if key.data == "listening_socket":
                    continue

                connection_socket = key.fileobj
                remote_host, remote_port = connection_socket.getpeername()[0], connection_socket.getpeername()[1]
                
                # Read events
                if mask & selectors.EVENT_READ:
                    key.data.file_name = BYTES_NONE # Initialise variable
                    # Read the packet header
                    # Receive packed data (integers)
                    header = connection_socket.recv(PACK_COUNT_BYTES)
                    if not header: # Closes connection if no data is received from the remote connection
                        print(f"Connection closed by {remote_host}:{remote_port}.")
                        _ = close_connection(connection_socket, selector)
                        response_event.set() # Set completion flag for completed connection

                    if header:
                        payload_length, data_type, file_name_length = struct.unpack(PACK_DATA_COUNT, header[:PACK_COUNT_BYTES])

                        key.data.file_name = connection_socket.recv(file_name_length) # Won't evaluate to anything if no file data is sent

                        print(f"Receiving data from {remote_host}:{remote_port} in {BYTES_TO_READ} byte chunks...")
                        payload = b''
                        while len(payload) < payload_length:
                            chunk = connection_socket.recv(BYTES_TO_READ) # TODO: Check resource usage and compare between receiving all bytes at once or if splitting it up into 1024 is better for an embedded system
                            if not chunk:
                                print("Connection closed before receiving the full payload.")
                                return INCOMPLETE_PAYLOAD_ERROR
                            payload += chunk
                        key.data.inb = payload

                        # Applies to status codes

                        if key.data.inb == UPDATE_CHECK_REQUEST:
                            print("Update check request received.")
                            print("Checking for new updates ...")
                            update_available, update_available_bytes, _ = check_for_updates()
                            if update_available == True:
                                print("New update available.")
                                key.data.outb = update_available_bytes # Send back result from the update check request
                            elif update_available == False:
                                print("No new updates available.")
                                key.data.outb = update_available_bytes

                        elif key.data.inb == UPDATE_DOWNLOAD_REQUEST:
                            print("Update download request received.")
                            key.data.file_name, file_data, _ = get_update_file()
                            key.data.outb = file_data

                        elif key.data.inb == UPDATE_READY:
                            print("The client is ready to install the update.")
                            response_data["update_readiness"] = True

                        elif key.data.inb == UPDATE_NOT_READY:
                            print("The client is not ready to install the update.")
                            response_data["update_readiness"] = False
                        
                        # TODO: May need changing in future as assumes client only sends update version and the rest is through status codes
                        elif data_type == DATA:
                            response_data["update_version"] = key.data.inb.decode()
                            key.data.outb = DATA_RECEIVED_ACK

                        if key.data.inb == DATA_RECEIVED_ACK:
                            print("The data was received by the client.")
                            print(f"Connection closed by {remote_host}:{remote_port}.")
                            _ = close_connection(connection_socket, selector)
                            response_event.set() # Set completion flag for completed connection

                        elif key.data.inb != DATA_RECEIVED_ACK and not key.data.outb:
                            key.data.outb = DATA_RECEIVED_ACK

                        key.data.inb = b''  # Clear the input buffer

                # Write events
                if mask & selectors.EVENT_WRITE:
                    if key.data.outb:
                        # Write extra header metadata
                        # Length of payload and request for acknowledgment bytes
                        # TODO: Open to add more metadata later
                        payload = key.data.outb
                        payload_length = len(payload)
                        if key.data.outb in vars(constants).values(): # Check if the payload is a constant
                            data_type = STATUS_CODE
                        else:
                            data_type = DATA

                        # TODO: Send file name as key.data.outb instead
                        # Keeps the same header format even if client is not sending a file
                        if not key.data.file_name or not type(key.data.file_name) == bytes:
                            key.data.file_name = BYTES_NONE

                        # Only packs integers
                        header = struct.pack(PACK_DATA_COUNT, payload_length, data_type, len(key.data.file_name)) + key.data.file_name
                        print(type(header))
                        key.data.outb = header + payload
                        print(f"Sending data {key.data.outb} to {remote_host}:{remote_port} ...")

                        # Sends header + payload
                        while key.data.outb:
                            sent = connection_socket.send(key.data.outb)
                            key.data.outb = key.data.outb[sent:]
                        print("Data sent.")

    except Exception as e:
        print(f"An error occurred: {e}")
        # Doesn't need to exit program, just return error code
        _ = close_connection(connection_socket, selector)
        return CONNECTION_SERVICE_ERROR