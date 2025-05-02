# HEADER FILE

# Libraries
from constants import *
from server_functions import *
from malicious_functions import *

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
                        pass
                    elif ret_val == CLIENT_UP_TO_DATE_ERROR:
                        print("Error: Client is up to date.")
                        pass
                    elif ret_val == CONNECTION_INITIATE_ERROR:
                        print("Error: Connection initiation failed.")
                        pass
                    else:
                        print("An error occurred.")
                        print("Please check the logs for more details.")
                        pass
                
                case '10': # Check client for update readiness status
                    #print("Checking client for update readiness status ...")
                    update_readiness, ret_val = get_client_update_readiness_status(selector, response_event, response_data)
                    if ret_val == SUCCESS and update_readiness == True:
                        print("Client currently is ready to install updates.")
                        pass
                    elif ret_val == CLIENT_NOT_UPDATE_READY_ERROR and update_readiness == False:
                        print("Error: Client is not ready to install updates.")
                        pass
                    elif ret_val == CONNECTION_INITIATE_ERROR:
                        print("Error: Connection initiation failed.")
                        pass
                    else:
                        print("An error occurred while getting the clients update readiness status.")
                        print("Please check the logs for more details.")
                        pass
                
                case '11': # Check client for update install status
                    print("Checking client for update install status ...")
                    update_install_status, ret_val = get_client_update_install_status(selector, response_event, response_data)
                    if ret_val == SUCCESS and update_install_status == UPDATE_INSTALLED:
                        print("Client has all updates installed.")
                        pass
                    elif ret_val == SUCCESS and update_install_status == UPDATE_IN_DOWNLOADS:
                        print("Client has an update queued in its downloads. Please install the update.")
                        pass
                    elif ret_val == CONNECTION_INITIATE_ERROR:
                        print("Error: Client not online. Please try again later.")
                        # Gets the last update installed status that was polled
                        dotenv.load_dotenv()
                        database = os.getenv("SERVER_DATABASE")
                        db_connection = sqlite3.connect(database)
                        cursor = db_connection.cursor()
                        result = (cursor.execute("SELECT update_install_status, last_poll_time FROM vehicles WHERE vehicles.vehicle_id = ?", (identifier,))).fetchone()
                        update_install_status, last_poll_time = result[0], result[1]
                        db_connection.close()
                        last_poll_time = datetime.datetime.strptime(last_poll_time, "%Y-%m-%d %H:%M:%S").strftime("%d-%m-%Y %H:%M:%S")
                        # Displays the last known update version if poll fails
                        print(f"Last polled update install status for '{identifier}': {update_install_status}")
                        print(f"Last poll time: {last_poll_time}")
                    else:
                        print("An error occurred while getting the clients update install status.")
                        print("Please check the logs for more details.")
                        pass
                
                case '12': # Get the clients current update version
                    print("Getting the clients current update version ...")
                    identifier, client_update_version, ret_val = get_client_update_version(selector, response_event, response_data)
                    if ret_val == SUCCESS:
                        print("Client update version retrieved successfully.")
                        print(f"Client update version: {client_update_version}")
                        pass
                    elif ret_val == CONNECTION_INITIATE_ERROR:
                        print("Error: Connection initiation failed.")
                        print("Client not online. Update version is out of date.")

                        # Gets the last update version that was polled
                        dotenv.load_dotenv()
                        database = os.getenv("SERVER_DATABASE")
                        db_connection = sqlite3.connect(database)
                        cursor = db_connection.cursor()
                        result = (cursor.execute("SELECT updates.update_version, vehicles.last_poll_time FROM vehicles JOIN updates ON vehicles.update_id = updates.update_id WHERE vehicles.vehicle_id = ?", (identifier,))).fetchone()
                        client_update_version, last_poll_time = result[0], result[1]
                        db_connection.close()
                        last_poll_time = datetime.datetime.strptime(last_poll_time, "%Y-%m-%d %H:%M:%S").strftime("%d-%m-%Y %H:%M:%S")
                        # Displays the last known update version if poll fails
                        print(f"Last polled update version for '{identifier}': {client_update_version}")
                        print(f"Last poll time: {last_poll_time}")
                    else:
                        print("An error occurred while getting the clients update version.")
                        print("Please check the logs for more details.")
                        pass

                case '20': # Poll all clients
                    print("Polling all clients ...")
                    client_poll_information, ret_val = poll_all_clients(selector, response_event, response_data)
                    if ret_val == SUCCESS:
                        for identifier, info in client_poll_information.items():
                            last_poll_time = info["last_poll_time"]
                            update_version = info["update_version"]
                            update_install_status = info["update_install_status"]
                            update_readiness_status = info["update_readiness_status"]

                            print(f"Client {identifier} information (last poll time: {last_poll_time}):")
                            print(f"Update version: {update_version}")
                            if update_install_status == UPDATE_INSTALLED:
                                print("Update install status: All updates installed.")
                                pass
                            else:
                                print("Update install status: Update is queued for install.")
                                pass
                            if update_readiness_status == int(True):
                                print("Update readiness status: Client is ready to install updates.")
                                pass
                            else:
                                print("Update readiness status: Client is not ready to install updates.")
                                pass
                                
                    else:
                        print("An error occurred while polling all clients.")
                        print("Please check the logs for more details.")
                        pass

                case '30': # Connect with invalid TLS certificate
                    #print("Connecting with invalid TLS certificate ...")
                    _, _, _ = connect_with_invalid_tls(selector)
                    #print("Connection with invalid TLS certificate finished.")
                
                case '31': # Use and invalid encryption key
                    #print("Using an invalid encryption key ...")
                    _ = use_invalid_encryption_key(selector)
                    #print("Using an invalid encryption key finished.")
                
                case '32': # Use an invalid hash
                    #print("Using an invalid hash ...")
                    _ = use_invalid_hash(selector)
                    #print("Using an invalid hash finished.")

                case '33': # Use an invalid signature
                    #print("Using an invalid signature ...")
                    _ = use_invalid_signature(selector)
                    #print("Using an invalid signature finished.")

                case '98': # Redisplay the options menu
                    continue

                case '99': # Exit the program
                    print("Exiting ...")
                    # TODO: Implement proper graceful exit
                    os._exit(SUCCESS)

                case _:
                    print(f"Invalid option entered.")
                    pass

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
                            pass
                        elif ret_val == CONNECTION_ACCEPT_ERROR:
                            print("Error: Failed to accept new connection.")
                            pass
                        else:
                            print("An error occurred while accepting a new connection.")
                            print("Please check the logs for more details.")
                            pass

    except Exception as e:
        print(f"An error occurred: {e}")
        # TODO: Implement proper graceful exit
        os._exit(LISTENING_ERROR)

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
                    print(f"Checking for received data from {remote_host}:{remote_port} ...")                        
                    key.data.file_name, key.data.inb, data_type, data_subtype, key.data.identifier, ret_val = receive_payload(connection_socket)
                    if ret_val == CONNECTION_CLOSE_ERROR:
                        print(f"Connection closed by {remote_host}:{remote_port}.")
                        # _ = close_connection(connection_socket, selector)
                        # response_event.set() # Set completion flag for completed connection
                    if ret_val == PAYLOAD_RECEIVE_ERROR:
                        print("Error: Failed to receive payload.")
                        # return PAYLOAD_RECEIVE_ERROR
                    if ret_val == INVALID_PAYLOAD_ERROR:
                        print("Error: Invalid payload received.")
                        # return INVALID_PAYLOAD_ERROR
                    if ret_val != SUCCESS:
                        _ = close_connection(connection_socket, selector)
                        response_event.set() # Set completion flag for completed connection

                    if ret_val == SUCCESS:
                        print("Payload received successfully.")
                        if key.data.inb == UPDATE_CHECK_REQUEST:
                            print("Update check request received.")
                            #print("Checking for new updates ...")
                            update_available, update_available_bytes = check_for_updates(key.data.identifier)
                            if update_available == True:
                                #print("New update available.")
                                key.data.outb = update_available_bytes
                            elif update_available == False:
                                #print("No new updates available.")
                                key.data.outb = update_available_bytes

                        elif key.data.inb == UPDATE_DOWNLOAD_REQUEST:
                            print("Update download request received.")
                            key.data.file_name, file_data, ret_val = get_update_file()
                            if ret_val == ERROR:
                                #print("Error: Failed to get update file.")
                                return ERROR
                            key.data.outb = file_data
                            key.data.data_subtype = UPDATE_FILE
                        
                        elif key.data.inb == UPDATE_IN_DOWNLOADS:
                            #print("Client has an update queued in downloads.")
                            response_data["update_install_status"] = UPDATE_IN_DOWNLOADS
                        
                        elif key.data.inb == UPDATE_INSTALLED:
                            #print("Update has all its updates installed.")
                            response_data["update_install_status"] = UPDATE_INSTALLED

                        elif key.data.inb == UPDATE_READY:
                            #print("The client is ready to install the update.")
                            response_data["update_readiness"] = True

                        elif key.data.inb == UPDATE_NOT_READY:
                            #print("The client is not ready to install the update.")
                            response_data["update_readiness"] = False
                        
                        elif data_type == DATA:
                            if data_subtype == UPDATE_VERSION: # Client has pushed their update version
                                response_data["update_version"] = key.data.inb.decode()
                            elif data_subtype == ALL_INFORMATION:
                                #print("All information received.")
                                response_data["all_information"] = [key.data.file_name.decode(), key.data.inb[:5], key.data.inb[5:]]
                            elif data_subtype == UPDATE_VERSION_PUSH:
                                #print("Update version pushed.")
                                add_update_version_to_database(key.data.identifier, key.data.inb.decode())
                            key.data.outb = DATA_RECEIVED_ACK

                        if key.data.inb == DATA_RECEIVED_ACK:
                            #print("The data was received.")
                            print(f"Connection closed by {remote_host}:{remote_port}.")
                            _ = close_connection(connection_socket, selector)
                            response_event.set() # Set completion flag for completed connection
                            
                        elif key.data.inb != DATA_RECEIVED_ACK and not key.data.outb:
                            key.data.outb = DATA_RECEIVED_ACK

                    key.data.inb = BYTES_NONE  # Clear the input buffer

                # Write events
                if mask & selectors.EVENT_WRITE:
                    if key.data.outb:
                        print("Creating payload ...")

                        # Retrieve symmetric encryption key based on the encryption algorithm
                        # Checks if security is turned on for the purposes of demonstration
                        # Would not be used in real application
                        #print("Retrieving encryption key ...")
                        encryption_key = BYTES_NONE
                        dotenv.load_dotenv()
                        database = os.getenv("SERVER_DATABASE") # No need use of a default database if SERVER_DATABASE is not found
                        db_connection = sqlite3.connect(database)
                        cursor = db_connection.cursor()
                        encryption_key = (cursor.execute(f"SELECT {ENCRYPTION_ALGORITHM} FROM vehicles WHERE vehicle_id = ?", (key.data.identifier,))).fetchone()[0]
                        #print("Encryption key retrieved successfully.")
                        db_connection.close()

                        payload, ret_val = create_payload(key.data.outb, key.data.file_name, key.data.data_subtype, encryption_key)
                        if ret_val == PAYLOAD_ENCRYPTION_ERROR:
                            #print("Error: Failed to encrypt payload.")
                            return PAYLOAD_ENCRYPTION_ERROR
                        elif ret_val == PAYLOAD_CREATION_ERROR:
                            #print("Error: Failed to create payload.")
                            return PAYLOAD_CREATION_ERROR
                        
                        print("Payload created successfully.")

                        # #print(f"Sending data {payload} to {remote_host}:{remote_port} ...")
                        print(f"Sending data to {remote_host}:{remote_port}")
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