# HEADER FILE

# Libraries
import selectors
import os
import struct
import random
import re
from constants import *
from client_functions import *
from cryptographic_functions import *

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
                    ret_val = install_update(selector, response_event, response_data)
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

                case '22':
                    print("Displaying the update version ...")
                    update_version, _, ret_val = get_update_version()
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
                # AI assistance used for the idea of how to create the custom header for the packet

                # Service active socket connections, not the listening socket
                if key.data == "listening_socket":
                    continue

                connection_socket = key.fileobj
                remote_host, remote_port = connection_socket.getpeername()[0], connection_socket.getpeername()[1]
                
                # Read events
                if mask & selectors.EVENT_READ:
                    print(f"Receiving data from {remote_host}:{remote_port} in {BYTES_TO_READ} byte chunks...")
                    key.data.file_name, key.data.inb, data_type, data_subtype, ret_val = receive_payload(connection_socket)
                    if ret_val == CONNECTION_CLOSE_ERROR:
                        print(f"Connection closed by {remote_host}:{remote_port}.")
                        _ = close_connection(connection_socket, selector)
                        response_event.set() # Set completion flag for completed connection
                    if ret_val == PAYLOAD_RECEIVE_ERROR:
                        print("Error: Failed to receive payload.")
                        return PAYLOAD_RECEIVE_ERROR

                    if ret_val == SUCCESS:
                        if key.data.inb == UPDATE_AVALIABLE:
                            print("There is an update available.")
                            response_data["update_available"] = True
                            
                        elif key.data.inb == UPDATE_NOT_AVALIABLE:
                            print("There is no update available.")
                            response_data["update_available"] = False

                        elif key.data.inb == UPDATE_READINESS_STATUS_REQUEST:
                            print("Update readiness status request received.")
                            update_readiness, _, _ = check_update_readiness_status()
                            if update_readiness == True:
                                print("Client is ready to receive the update.")
                                key.data.outb = UPDATE_READY
                            elif update_readiness == False:
                                print("Client is not ready to receive the update.")
                                key.data.outb = UPDATE_NOT_READY

                        elif key.data.inb == UPDATE_VERSION_REQUEST:
                            print("Update version request received.")
                            _, update_version_bytes, _ = get_update_version()
                            key.data.outb = update_version_bytes
                            key.data.data_subtype = UPDATE_VERSION

                        elif data_type == DATA:
                            if data_subtype == UPDATE_FILE:
                                ret_val = write_update_file_to_database(key.data.file_name.decode(), key.data.inb)
                                if ret_val == SUCCESS:
                                    print("Update file written to database successfully.")
                                elif ret_val == DOWNLOAD_UPDATE_ERROR:
                                    print("Error: Failed to write update file to database.")
                                    return DOWNLOAD_UPDATE_ERROR
                                else:
                                    print("An error occurred while retrieving the database name.")
                                    print("Please check the logs for more details.")
                                    return ERROR

                        if key.data.inb == DATA_RECEIVED_ACK:
                            print("The data was received.")
                            print(f"Connection closed by {remote_host}:{remote_port}.")
                            _ = close_connection(connection_socket, selector)
                            response_event.set() # Set completion flag for completed connection
                            
                        elif key.data.inb != DATA_RECEIVED_ACK and not key.data.outb:
                            key.data.outb = DATA_RECEIVED_ACK

                    key.data.inb = BYTES_NONE  # Clear the input buffer
                    key.data.file_name = BYTES_NONE

                # Write events
                if mask & selectors.EVENT_WRITE:
                    if key.data.outb:
                        print("Creating payload ...")
                        payload, ret_val = create_payload(key.data.outb, key.data.file_name, key.data.data_subtype)
                        if ret_val == PAYLOAD_CREATION_ERROR:
                            print("Error: Failed to create payload.")
                            return PAYLOAD_CREATION_ERROR
                        
                        print(f"Sending data {payload} to {remote_host}:{remote_port} ...")
                        while payload:
                            sent = connection_socket.send(payload)
                            payload = payload[sent:]
                        key.data.outb = BYTES_NONE
                        print("Data sent.")

    except Exception as e:
        print(f"An error occurred: {e}")
        # Doesn't need to exit program, just return error code
        _ = close_connection(connection_socket, selector)
        return CONNECTION_SERVICE_ERROR