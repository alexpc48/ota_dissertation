# HEADER FILE

# Libraries
from constants import *
from client_functions import *
from cryptographic_functions import *

# Thread for displaying the options menu in a non-blocking way
def menu_thread(selector: selectors.SelectSelector, response_event: threading.Event, response_data: dict) -> None:
    try:
        while True:
            option = options_menu()
            match option:

                case '1': # Request update check from the server
                    print("Checking the server for updates ...")
                    _, ret_val = check_for_update(selector, response_event, response_data)
                    if ret_val == SUCCESS:
                        print("Update check completed successfully.")
                        print("There is a new update.")
                        pass
                    elif ret_val == NO_UPDATE_ERROR:
                        print("Update check completed successfully.")
                        print("There is no new udpate.")
                        pass
                    elif ret_val == CONNECTION_INITIATE_ERROR:
                        print("Error: Connection initiation failed.")
                        pass
                    else:
                        print("An error occurred while checking for an update.")
                        print("Please check the logs for more details.")
                        pass

                case '2': # Download updates from the server
                    process = psutil.Process(os.getpid())
                    print("Downloading updates from the server ...")
                    # ret_val = download_update(selector, response_event, response_data)
                    download_update_stats = {}
                    ret_val, download_update_stats = measure_operation(process, download_update, selector, response_event, response_data)
                    if ret_val == SUCCESS:
                        print("Update downloaded successfully.")
                        os_type, _ = get_os_type()
                        dotenv.load_dotenv()
                        if os_type == "Windows":
                            diagnostics_file = "windows_client_diagnostics.csv"
                        elif os_type == "Linux":
                            diagnostics_file = "linux_client_diagnostics.csv"
                        security_operations = [download_update_stats]
                        _ = write_diagnostic_file('Downloading Update', diagnostics_file, security_operations)
                        pass
                    elif ret_val == QUEUED_UPDATE_ERROR:
                        print("Error: There is an update already queued for install.")
                        pass
                    else:
                        print("An error occurred while downloading an update.")
                        print("Please check the logs for more details.")
                        pass

                case '3': # Install the update
                    print("Installing the update ...")
                    ret_val = install_update(selector, response_event, response_data)
                    if ret_val == SUCCESS:
                        print("Update installed successfully.")
                        pass
                    elif ret_val == CLIENT_NOT_UPDATE_READY_ERROR:
                        print("Error: Client is not ready to receive the update.")
                        pass
                    elif ret_val == UPDATE_NOT_AVALIABLE_ERROR:
                        print("Error: There is no update queued for install.")
                        pass
                    elif ret_val == UPDATE_INSTALL_ERROR:
                        print("Error: There was an error installing the update.")
                        pass
                    else:
                        print("An error occurred while installing the update.")
                        print("Please check the logs for more details.")
                        pass

                case '20': # Check the update readiness
                    print("Displaying the update readiness status ...")
                    update_readiness_status, _, ret_val = check_update_readiness_status()
                    if ret_val == SUCCESS:
                        print(f"Current update install readiness status: {update_readiness_status}")
                        pass
                    elif ret_val == CHECK_UPDATE_ERROR:
                        print("Error: Update readiness status check failed.")
                        pass
                    else:
                        print("An error occured while checking the update readiness status.")
                        print("Please check the logs for more details.")
                        pass

                case '21': # Check the installation status
                    print("Displaying the installation status ...")
                    ret_val = check_update_in_downloads_buffer()
                    if ret_val == SUCCESS:
                        print("All updates have been installed.")
                        pass
                    elif ret_val == QUEUED_UPDATE_ERROR:
                        print("There is an update in the downloads buffer.")
                        pass
                    else:
                        print("An error occurred while checking the downloads buffer.")
                        print("Please check the logs for more details.")
                        return ERROR

                case '22': # Displays the current update version installed
                    print("Displaying the update version ...")
                    update_version, _, ret_val = get_update_version()
                    if ret_val == SUCCESS:
                        print("Update version checked successfully.")
                        print(f"Update version: {update_version}")
                        pass
                    else:
                        print("An error occured while checking the update version.")
                        print("Please check the logs for more details.")
                        pass

                case '23': # Displays time of update installation
                    print("Displaying the update installation time ...")
                    update_install_time, ret_val = get_update_install_time()
                    if ret_val == SUCCESS:
                        print("Update installation time checked successfully.")
                        print(f"Update installation time: {update_install_time}")
                        pass
                    else:
                        print("An error occured while checking the update installation time.")
                        print("Please check the logs for more details.")
                        pass

                case '30': # Rollback the update
                    print("Rolling back the update ...")
                    ret_val = rollback_update_install(selector, response_event, response_data)
                    if ret_val == SUCCESS:
                        print("Update rolled back successfully.")
                        pass
                    elif ret_val == NO_ROLLBACK_UPDATES_ERROR:
                        print("Error: There are no updates to rollback to.")
                        pass
                    else:
                        print("An error occurred while rolling back the update.")
                        print("Please check the logs for more details.")
                        pass

                case '31': # Change the update readiness status
                    print("Changing the update install readiness status ...")
                    ret_val = change_update_readiness()
                    if ret_val == SUCCESS:
                        print("Update install readiness status changed successfully.")
                        pass
                    elif ret_val == UPDATE_STATUS_REPEAT_ERROR:
                        print("Error: Update readiness status is already set to the same value.")
                        pass
                    else:
                        print("An error occured while changing the update readiness status.")
                        print("Please check the logs for more details.")
                        pass

                case '98': # Redisplay the options menu
                    continue

                case '99': # Exit the program
                    print("Exiting ...")
                    # TODO: Implement proper graceful exit
                    os._exit(SUCCESS)
                
                case _: # Default case for invalid options
                    print(f"Invalid option entered.")
                    pass

    except KeyboardInterrupt:
        print("Exiting due to keyboard interrupt ...")
        os._exit(KEYBOARD_INTERRUPT)

    except Exception as e:
        print(f"An error occurred: {e}")
        # TODO: Implement proper graceful exit
        os._exit(ERROR)

# Thread for constatntly listening for connections from the server
def listen(selector: selectors.SelectSelector) -> None:
    try:
        while True:
            # Get list of events from the selector
            timeout_interval = random.randint(1, 10)
            events = selector.select(timeout=timeout_interval) # Refreshes in random intervals to avoid connection collisions
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

# Thread for servicing active connections
def service_connection(selector: selectors.SelectSelector, response_event: threading.Event, response_data: dict) -> int:
    try:
        while True:

            # Get list of events from the selector
            events = selector.select(timeout=0.1) # Refreshes for new events
            for key, mask in events:

                # Service active socket connections only, not the listening socket
                if key.data == "listening_socket":
                    continue

                connection_socket = key.fileobj
                remote_host, remote_port = connection_socket.getpeername()[0], connection_socket.getpeername()[1]

                # Read events
                if mask & selectors.EVENT_READ:
                    print(f"Checking for received data from {remote_host}:{remote_port} ...")                        
                    key.data.file_name, key.data.inb, data_type, data_subtype, _, ret_val = receive_payload(connection_socket)
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
                        if key.data.inb == UPDATE_AVALIABLE:
                            #print("There is an update available.")
                            response_data["update_available"] = True
                            
                        elif key.data.inb == UPDATE_NOT_AVALIABLE:
                            #print("There is no update available.")
                            response_data["update_available"] = False

                        elif key.data.inb == UPDATE_READINESS_STATUS_REQUEST:
                            print("Update readiness status request received.")
                            #print("Checking the update readiness status ...")
                            update_readiness, _, _ = check_update_readiness_status()
                            if update_readiness == True:
                                #print("Client is ready to receive the update.")
                                key.data.outb = UPDATE_READY
                            elif update_readiness == False:
                                #print("Client is not ready to receive the update.")
                                key.data.outb = UPDATE_NOT_READY

                        elif key.data.inb == UPDATE_VERSION_REQUEST:
                            print("Update version request received.")
                            #print("Retrieving the update version ...")
                            _, update_version_bytes, ret_val = get_update_version()
                            if ret_val == ERROR:
                                #print("An error occurred while retrieving the update version.")
                                #print("Please check the logs for more details.")
                                return ERROR
                            key.data.outb = update_version_bytes
                            key.data.data_subtype = UPDATE_VERSION

                        elif key.data.inb == INSTALL_STATUS_REQUEST:
                            print("Installation status request received.")
                            #print("Retrieving the installation status ...")
                            ret_val = check_update_in_downloads_buffer()
                            if ret_val == QUEUED_UPDATE_ERROR:
                                key.data.outb = UPDATE_IN_DOWNLOADS
                            elif ret_val == SUCCESS:
                                key.data.outb = UPDATE_INSTALLED
                            else:
                                # print("An error occurred while checking the downloads buffer.")
                                # print("Please check the logs for more details.")
                                return ERROR

                        elif key.data.inb == ALL_INFORMATION_REQUEST:
                            print("All information request received.")
                            #print("Retrieving all information ...")
                            update_version_bytes, update_install_status, update_readiness_bytes, ret_val = get_all_information()
                            if ret_val == ERROR:
                                #print("An error occurred while retrieving all information.")
                                #print("Please check the logs for more details.")
                                return ERROR
                            key.data.file_name = update_version_bytes # File name is the version number
                            key.data.outb = update_install_status + update_readiness_bytes # Update readiness status + update installed status
                            key.data.data_subtype = ALL_INFORMATION

                        elif data_type == DATA:
                            if data_subtype == UPDATE_FILE:
                                ret_val = write_update_file_to_database(key.data.file_name.decode(), key.data.inb)
                                if ret_val == SUCCESS:
                                    #print("Update file written to database successfully.")
                                    key.data.file_name = BYTES_NONE
                                elif ret_val == DOWNLOAD_UPDATE_ERROR:
                                    #print("Error: Failed to write update file to database.")
                                    return DOWNLOAD_UPDATE_ERROR
                                else: # ERROR will be from getting database name
                                    #print("An error occurred while retrieving the database name.")
                                    #print("Please check the logs for more details.")
                                    return ERROR

                        # Check if the data received is an acknowledgment for all data commmunications finished
                        if key.data.inb == DATA_RECEIVED_ACK:
                            print(f"Connection closed by {remote_host}:{remote_port}.")
                            _ = close_connection(connection_socket, selector)
                            response_event.set() # Set completion flag for completed connection
                            
                        # Send an acknowledgment if the data was received and nothing needs to be sent back
                        elif key.data.inb != DATA_RECEIVED_ACK and not key.data.outb:
                            key.data.outb = DATA_RECEIVED_ACK

                    key.data.inb = BYTES_NONE  # Clear the input buffer

                # Write events
                if mask & selectors.EVENT_WRITE:
                    if key.data.outb:
                        print("Creating payload ...")
                        
                        database, ret_val = get_client_database()
                        if ret_val == ERROR:
                            print("An error occurred while retrieving the database name.")
                            print("Please check the logs for more details.")
                            return ERROR
                        
                        # Retrieve symmetric encryption key based on the encryption algorithm
                        # Checks if security is turned on for the purposes of demonstration
                        # Would not be used in real application
                        #print("Retrieving encryption key ...")
                        encryption_key = BYTES_NONE
                        db_connection = sqlite3.connect(database)
                        cursor = db_connection.cursor()
                        encryption_key = (cursor.execute(f"SELECT {ENCRYPTION_ALGORITHM} FROM cryptographic_data LIMIT 1")).fetchone()[0]
                        #print("Encryption key retrieved successfully.")
                        db_connection.close()

                        payload, ret_val = create_payload(key.data.outb, key.data.file_name, key.data.data_subtype, encryption_key)
                        if ret_val == PAYLOAD_ENCRYPTION_ERROR:
                            print("Error: Failed to encrypt payload.")
                            return PAYLOAD_ENCRYPTION_ERROR
                        elif ret_val == PAYLOAD_CREATION_ERROR:
                            print("Error: Failed to create payload.")
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
        _ = close_connection(connection_socket, selector)
        return CONNECTION_SERVICE_ERROR