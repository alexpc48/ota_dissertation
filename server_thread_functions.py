# HEADER FILE

# Libraries
from constants import *
from server_functions import *

dotenv.load_dotenv(override=True)

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
                    elif ret_val == CONNECTION_INITIATE_ERROR:
                        print("Error: Connection initiation failed.")
                    else:
                        print("An error occurred.")
                        print("Please check the logs for more details.")
                
                # case '10': # Check client for update readiness status
                #     print("Checking client for update readiness status ...")
                #     update_readiness, ret_val = get_client_update_readiness_status(selector, response_event, response_data)
                #     if ret_val == SUCCESS and update_readiness == True:
                #         print("Client currently is ready to install updates.")
                #     elif ret_val == CLIENT_NOT_UPDATE_READY_ERROR and update_readiness == False:
                #         print("Error: Client is not ready to install updates.")
                #     elif ret_val == CONNECTION_INITIATE_ERROR:
                #         print("Error: Connection initiation failed.")
                #     else:
                #         print("An error occurred while getting the clients update readiness status.")
                #         print("Please check the logs for more details.")

                case '11':
                    continue
                
                case '12': # Get the clients current update version
                    print("Getting the clients current update version ...")
                    identifier, client_update_version, ret_val = get_client_update_version(selector, response_event, response_data)
                    if ret_val == SUCCESS:
                        print(f"Client update version: {client_update_version}")
                        print("Client update version retrieved successfully.")
                    elif ret_val == CONNECTION_INITIATE_ERROR:
                        print("Error: Connection initiation failed.")
                        print("Client not online. Update version is out of date.")

                        # Gets the last update version that was polled
                        dotenv.load_dotenv()
                        database = os.getenv("SERVER_DATABASE")
                        db_connection = sqlite3.connect(database)
                        cursor = db_connection.cursor()
                        # TODO: Test query
                        result = (cursor.execute("SELECT updates.update_version, vehicles.last_poll_time FROM vehicles JOIN updates ON vehicles.update_id = updates.update_id WHERE vehicles.vehicle_id = ?", (identifier,))).fetchone
                        client_update_version, last_poll_time = result[0], result[1]
                        db_connection.close()
                        # Displays the last known update version if poll fails
                        print(f"Last polled update version for '{identifier}': {client_update_version}")
                        print(f"Last poll time: {last_poll_time}")
                    else:
                        print("An error occurred while getting the clients update version.")
                        print("Please check the logs for more details.")

                case '20':
                    continue

                case '30':
                    continue

                # case '40':
                    # _ = change_security_status()

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
                            print("An error occurred while accepting a new connection.")
                            print("Please check the logs for more details.")

    except Exception as e:
        print(f"An error occurred: {e}")
        # TODO: Implement proper graceful exit
        os._exit(LISTENING_ERROR)


import ssl 
# Service current connecitons
def service_connection(selector: selectors.SelectSelector, response_event: threading.Event, response_data: dict) -> int:
    try:
        while True:
            # Get list of events from the selector
            timeout_interval = random.randint(1, 10)
            events = selector.select(timeout=timeout_interval)
            for key, mask in events:

                # Service active socket connections only, not the listening socket
                if key.data == "listening_socket":
                    continue

                connection_socket = key.fileobj
                remote_host, remote_port = connection_socket.getpeername()[0], connection_socket.getpeername()[1]
                
                # Read events
                if mask & selectors.EVENT_READ:
                    print(f"Receiving data from {remote_host}:{remote_port} in {BYTES_TO_READ} byte chunks...")

                    buffer = b''
                    delimiter = b'\n'
                    while delimiter not in buffer:
                        try:
                            chunk = connection_socket.recv(BYTES_TO_READ)
                            if not chunk:
                                # Connection closed
                                break
                            buffer += chunk

                        except ssl.SSLWantReadError:
                            print("SSLWantReadError: Waiting for more data to be readable...")

                        except ssl.SSLWantWriteError:
                            print("SSLWantWriteError: Waiting until socket is writable...")
                        except BlockingIOError:
                            print("Socket is busy, waiting for data...")
                        except socket.error as e:
                            print(f"Socket error during recv: {e}")
                            return ERROR
                        except ssl.SSLError as e:
                            print(f"SSL error during recv: {e}")
                            return ERROR
                        except Exception as e:
                            print(f"Unexpected error during recv: {e}")
                            return ERROR
                    if delimiter in buffer:
                        print(buffer)
                    return SUCCESS
                    
                    key.data.file_name, key.data.inb, data_type, data_subtype, key.data.identifier, ret_val = receive_payload(connection_socket)
                    if ret_val == CONNECTION_CLOSE_ERROR:
                        print(f"Connection closed by {remote_host}:{remote_port}.")
                        _ = close_connection(connection_socket, selector)
                        response_event.set() # Set completion flag for completed connection
                    if ret_val == PAYLOAD_RECEIVE_ERROR:
                        print("Error: Failed to receive payload.")
                        return PAYLOAD_RECEIVE_ERROR
                    if ret_val == INVALID_PAYLOAD_ERROR:
                        print("Error: Invalid payload received.")
                        return INVALID_PAYLOAD_ERROR
                    
                    if ret_val == SUCCESS:

                        if key.data.inb == UPDATE_CHECK_REQUEST:
                            print("Update check request received.")
                            print("Checking for new updates ...")
                            update_available, update_available_bytes = check_for_updates()
                            if update_available == True:
                                print("New update available.")
                                key.data.outb = update_available_bytes
                            elif update_available == False:
                                print("No new updates available.")
                                key.data.outb = update_available_bytes

                        elif key.data.inb == UPDATE_DOWNLOAD_REQUEST:
                            print("Update download request received.")
                            key.data.file_name, file_data, ret_val = get_update_file()
                            if ret_val == ERROR:
                                print("Error: Failed to get update file.")
                                return ERROR
                            key.data.outb = file_data
                            key.data.data_subtype = UPDATE_FILE

                        elif key.data.inb == UPDATE_READY:
                            print("The client is ready to install the update.")
                            response_data["update_readiness"] = True

                        elif key.data.inb == UPDATE_NOT_READY:
                            print("The client is not ready to install the update.")
                            response_data["update_readiness"] = False
                        
                        elif data_type == DATA:
                            if data_subtype == UPDATE_VERSION: # Client has pushed their update version
                                response_data["update_version"] = key.data.inb.decode()
                            # elif data_subtype == UPDATE_VERSION_PUSH:
                            #     _ = store_update_version(key.data.inb.decode(), selector, connection_socket)
                            key.data.outb = DATA_RECEIVED_ACK

                        if key.data.inb == DATA_RECEIVED_ACK:
                            print("The data was received.")
                            print(f"Connection closed by {remote_host}:{remote_port}.")
                            _ = close_connection(connection_socket, selector)
                            response_event.set() # Set completion flag for completed connection
                            
                        elif key.data.inb != DATA_RECEIVED_ACK and not key.data.outb:
                            key.data.outb = DATA_RECEIVED_ACK

                    key.data.inb = BYTES_NONE  # Clear the input buffer

                # Write events
                if mask & selectors.EVENT_WRITE:
                    print('writing')
                    if key.data.outb:
                        print("Creating payload ...")

                        # Retrieve symmetric encryption key based on the encryption algorithm
                        # Checks if security is turned on for the purposes of demonstration
                        # Would not be used in real application
                        encryption_key = BYTES_NONE
                        if SECURITY_MODE == 1:
                            dotenv.load_dotenv()
                            database = os.getenv("SERVER_DATABASE") # Not using a default database
                            db_connection = sqlite3.connect(database)
                            cursor = db_connection.cursor()
                            encryption_key = (cursor.execute(f"SELECT {ENCRYPTION_ALGORITHM} FROM vehicles WHERE vehicle_id = ?", (key.data.identifier,))).fetchone()[0]
                            db_connection.close()

                        payload, ret_val = create_payload(key.data.outb, key.data.file_name, key.data.data_subtype, encryption_key)
                        if ret_val == PAYLOAD_ENCRYPTION_ERROR:
                            print("Error: Failed to encrypt payload.")
                            return PAYLOAD_ENCRYPTION_ERROR
                        elif ret_val == PAYLOAD_CREATION_ERROR:
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