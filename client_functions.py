# HEADER FILE

# Libraries
import threading
import platform

from constants import *
from functions import *

# Displays the options menu for client functions
def options_menu() -> str:
    print("\n-------------------------------------------------------------------------------------------")
    print("Options:")
    print("-------------------------------------------------------------------------------------------")
    print("1. Check for new updates")
    print("2. Download new updates")
    print("3. Install downloaded updates")
    #print("-------------------------------------------------------------------------------------------")
    #print("10. Change the update readiness status")
    print("-------------------------------------------------------------------------------------------")
    print("20. Display the update readiness status")
    print("21. Display the update install status")
    print("22. Display the update version")
    print("23. Display the update install time")
    print("-------------------------------------------------------------------------------------------")
    print("30. [DEMO] Rollback to the previous update")
    print("31. [DEMO] Change the update install readiness status")
    print("-------------------------------------------------------------------------------------------")
    print("98. Redisplay the options menu")
    print("99. Exit")
    print("-------------------------------------------------------------------------------------------")

    return input("Enter an option: ")

# Gets the OS type of the client
def get_os_type() -> typing.Tuple[str, int]:
    try:
        os_type = platform.system()
        if os_type != "Windows" and os_type != "Linux":
            # #print(f"Unknown operating system: {os_type}")
            return STR_NONE, ERROR
        return os_type, SUCCESS
    
    except Exception as e:
        #print(f"An error occurred: {e}")
        return STR_NONE, ERROR
    
# Gets which client database to connect to based on the OS type
def get_client_database() -> typing.Tuple[str, int]:
    try:
        os_type, ret_val = get_os_type()
        if ret_val == ERROR:
            #print("An error occurred while retrieving the OS type.")
            #print("Please check the logs for more details.")
            return STR_NONE, ERROR
        
        dotenv.load_dotenv()
        if os_type == "Windows":
            database = os.getenv("WINDOWS_CLIENT_DATABASE")
        elif os_type == "Linux":
            database = os.getenv("LINUX_CLIENT_DATABASE")
        else:
            #print(f"Unknown operating system: {os_type}")
            return STR_NONE, ERROR

        return database, SUCCESS

    except Exception as e:
        #print(f"An error occurred: {e}")
        return STR_NONE, ERROR

# Gets the server information from the database
def get_server_information() -> typing.Tuple[str, int, int]:
    try:
        database, ret_val = get_client_database()
        if ret_val == ERROR:
            #print("An error occurred while retrieving the database name.")
            #print("Please check the logs for more details.")
            return ERROR
        
        db_connection = sqlite3.connect(database)
        cursor = db_connection.cursor()
        # Get the server IP and port from the database
        result = (cursor.execute("SELECT server_ip, server_port FROM network_information WHERE network_id = 1")).fetchone()
        server_host, server_port = result[0], result[1]
        #print(f"Server IP: {server_host}, Server Port: {server_port}")
        db_connection.close()

        return server_host, server_port, SUCCESS
    
    except Exception as e:
        #print(f"An error occurred: {e}")
        return STR_NONE, INT_NONE, ERROR

# Checks the update readiness status in the database
def check_update_readiness_status() -> typing.Tuple[bool, bytes, int]:
    try:
        database, ret_val = get_client_database()
        if ret_val == ERROR:
            #print("An error occurred while retrieving the database name.")
            #print("Please check the logs for more details.")
            return BOOL_NONE, BYTES_NONE, ERROR
        
        db_connection = sqlite3.connect(database)
        cursor = db_connection.cursor()
        update_readiness_status = bool((cursor.execute("SELECT update_readiness_status FROM update_information WHERE update_entry_id = 1")).fetchone()[0])
        db_connection.close()

        if update_readiness_status == True:
            update_readiness_bytes = UPDATE_READY
        elif update_readiness_status == False:
            update_readiness_bytes = UPDATE_NOT_READY

        return update_readiness_status, update_readiness_bytes, SUCCESS
    
    except Exception as e:
        #print(f"An error occurred: {e}")
        return BOOL_NONE, BYTES_NONE, CHECK_UPDATE_ERROR

# Changes the update readiness status in the database
# Would change automatically based on the vehicle state (i.e., if the vehicle is in motion it would not be available to install an update)
# Manual changing for demonstration purposes
def change_update_readiness() -> int:
    try:
        database, ret_val = get_client_database()
        if ret_val == ERROR:
            #print("An error occurred while retrieving the database name.")
            #print("Please check the logs for more details.")
            return ERROR

        update_readiness_status, _, ret_val = check_update_readiness_status() # Ignore the bytes value
        #print(f"Update readiness status currently: {update_readiness_status}")

        update_readiness_change_value = str(input("Enter a new readiness status (True/False): ")).lower()
        if update_readiness_change_value == str(update_readiness_status):
            #print(f"Update readiness status is already set to {update_readiness_status}.")
            return UPDATE_STATUS_REPEAT_ERROR
        elif update_readiness_change_value in ['true', 'false']: # Check if the input is valid
            #print("Changing update readiness status ...")
            if update_readiness_change_value == 'true':
                update_readiness_status = int(True)
            elif update_readiness_change_value == 'false':
                update_readiness_status = int(False)
        else:
            #print("Invalid input.")
            return ERROR

        db_connection = sqlite3.connect(database)
        cursor = db_connection.cursor()
        cursor.execute("UPDATE update_information SET update_readiness_status = ? WHERE update_entry_id = 1", (update_readiness_status,))
        db_connection.commit()
        db_connection.close()
        #print(f"Update readiness status changed to {update_readiness_status}.")
        
        return SUCCESS
    
    except Exception as e:
        #print(f"An error occurred: {e}")
        return ERROR

# Connects to the server
# Requests an update check from the server 
# The server will check its latest update against the one it has stored for the client and return the result
def check_for_update(selector: selectors.SelectSelector, response_event: threading.Event, response_data: dict) -> typing.Tuple[bool, int]:
    try:
        server_host, server_port, ret_val = get_server_information()
        if ret_val == ERROR:
            #print("An error occurred while retrieving the server information.")
            #print("Please check the logs for more details.")
            return BOOL_NONE, ERROR

        selector, connection_socket, ret_val = create_connection(server_host, server_port, selector)
        if ret_val == CONNECTION_INITIATE_ERROR:
            #print("Error: Connection initiation failed.")
            return BOOL_NONE, CONNECTION_INITIATE_ERROR
        
        key = selector.get_key(connection_socket)

        # Data to send to the server
        # Data requests the server to check for an update
        key.data.outb = UPDATE_CHECK_REQUEST

        # Clear the events and wait for the server response
        # Waits indefinitly, but in reality it should have a timeout value
        response_event.clear()
        response_event.wait(timeout=None)
        if not response_event.is_set():
            #print("Timeout waiting for client response.")
            return BOOL_NONE, CONNECTION_SERVICE_ERROR
        
        # Respsonse data is set during service of the connection
        update_avaliable = response_data.get("update_available")
        if update_avaliable == True:
            #print("An update is available.")
            pass
        elif update_avaliable == False:
            #print("There is no new update.")
            return BOOL_NONE, NO_UPDATE_ERROR
        else:
            #print("Invalid response from server.")
            return BOOL_NONE, ERROR

        response_data.clear()  # Clear the response data for the next request
        response_event.clear() # Clear the event for the next request

        return update_avaliable, SUCCESS
    
    except Exception as e:
        #print(f"An error occurred: {e}")
        return BOOL_NONE, CHECK_UPDATE_ERROR

# Checks if there is an update in the downloads buffer
def check_update_in_downloads_buffer() -> int:
    try:
        database, ret_val = get_client_database()
        if ret_val == ERROR:
            #print("An error occurred while retrieving the database name.")
            #print("Please check the logs for more details.")
            return ERROR
        
        db_connection = sqlite3.connect(database)
        cursor = db_connection.cursor()
        
        result = (cursor.execute("SELECT EXISTS (SELECT 1 FROM update_downloads)")).fetchone()
        if result[0]:
            # #print("An update is already queued for install.")
            # #print("Please install the update before downloading a new one.")
            db_connection.close()
            return QUEUED_UPDATE_ERROR

        return SUCCESS
    
    except Exception as e:
        #print(f"An error occurred: {e}")
        return ERROR


# Downloads the latest update from the server
def download_update(selector: selectors.SelectSelector, response_event: threading.Event, response_data: dict) -> int:
    try:        
        ret_val = check_update_in_downloads_buffer()
        if ret_val == QUEUED_UPDATE_ERROR:
            #print("An update is already queued for install.")
            #print("Please install the update before downloading a new one.")
            return QUEUED_UPDATE_ERROR
        elif ret_val == ERROR:
            #print("An error occurred while checking the downloads buffer.")
            #print("Please check the logs for more details.")
            return ERROR
        
        server_host, server_port, ret_val = get_server_information()
        if ret_val == ERROR:
            #print("An error occurred while retrieving the server information.")
            #print("Please check the logs for more details.")
            return ERROR

        # Removed checking for an update first before downloading
        # This way initiates another new connection - slow and uneeded
        # update_available, _ = check_for_update(selector, response_event, response_data)
        # if update_available == False:
        #     #print("No update available to download.")
        #     return UPDATE_NOT_AVALIABLE

        selector, connection_socket, ret_val = create_connection(server_host, server_port, selector)
        if ret_val == CONNECTION_INITIATE_ERROR:
            #print("Error: Connection initiation failed.")
            return CONNECTION_INITIATE_ERROR    

        key = selector.get_key(connection_socket)
        
        key.data.outb = UPDATE_DOWNLOAD_REQUEST

        response_event.clear()
        response_event.wait(timeout=None)
        if not response_event.is_set():
            #print("Timeout waiting for server response.")
            return CONNECTION_SERVICE_ERROR

        response_data.clear()  # Clear the response data for the next request
        response_event.clear() # Clear the event for the next request

        return SUCCESS
    
    except Exception as e:
        #print(f"An error occurred: {e}")
        return DOWNLOAD_UPDATE_ERROR
        
# Gets the current update version installed
def get_update_version() -> typing.Tuple[str, bytes, int]:
    try:
        database, ret_val = get_client_database()
        if ret_val == ERROR:
            #print("An error occurred while retrieving the database name.")
            #print("Please check the logs for more details.")
            return STR_NONE, BYTES_NONE, ERROR
        
        db_connection = sqlite3.connect(database)
        cursor = db_connection.cursor()
        update_version = (cursor.execute("SELECT update_version FROM update_information WHERE update_entry_id = 1")).fetchone()[0]
        db_connection.close()
        update_version_bytes = str.encode(update_version)
        return update_version, update_version_bytes, SUCCESS
        
    except Exception as e:
        #print(f"An error occurred: {e}")
        return STR_NONE, BYTES_NONE, ERROR
    
# Writes the update file received to the downloads buffer in the database
def write_update_file_to_database(update_file_name: str, file_data: bytes) -> int:
    try:      
        database, ret_val = get_client_database()
        if ret_val == ERROR:
            #print("An error occurred while retrieving the database name.")
            #print("Please check the logs for more details.")
            return ERROR
        
        db_connection = sqlite3.connect(database)
        cursor = db_connection.cursor()
        cursor.execute("INSERT INTO update_downloads (update_version, update_file) VALUES (?, ?)", (update_file_name, file_data))
        db_connection.commit()
        db_connection.close()

        return SUCCESS
    
    except Exception as e:
        #print(f"An error occurred: {e}")
        return DOWNLOAD_UPDATE_ERROR
    
# Installs the update from the downloads buffer in the database
def install_update(selector: selectors.SelectSelector, response_event: threading.Event, response_data: dict) -> int:
    try:
        # Checks if ready to install the update
        update_readiness_status, _, ret_val = check_update_readiness_status()
        if ret_val == SUCCESS and update_readiness_status == False:
                #print("Client is not ready to receive the update.")
                return CLIENT_NOT_UPDATE_READY_ERROR
        elif ret_val == ERROR or ret_val == CHECK_UPDATE_ERROR:
            #print("An error occurred while checking the update readiness status.")
            #print("Please check the logs for more details.")
            return ERROR

        # Check if there is an update queued for download
        ret_val = check_update_in_downloads_buffer()
        if ret_val == ERROR:
            #print("There is no update queued for install.")
            #print("Please download an update before installing.")
            return UPDATE_NOT_AVALIABLE_ERROR
        
        database, ret_val = get_client_database()
        if ret_val == ERROR:
            #print("An error occurred while retrieving the database name.")
            #print("Please check the logs for more details.")
            return ERROR
        
        db_connection = sqlite3.connect(database)
        cursor = db_connection.cursor()

        result = (cursor.execute("SELECT update_version, update_file FROM update_downloads")).fetchone()
        update_file_name, file_data = result[0], result[1]

        # In reality would install to the vehicle
        # To simulate, it is being installed to a folder location
        # Move the current installed update to the rollback data database

        # Retrieve the current installed update version and file
        current_update = (cursor.execute("SELECT update_version FROM update_information WHERE update_entry_id = 1")).fetchone()[0]
        current_file_path = os.path.join(INSTALL_LOCATION, current_update)

        # No file upon first initialisation of demonstration system, so nothing to remove to rollback database
        try:
            with open(current_file_path, 'rb') as current_file:
                current_file_data = current_file.read()
            # Insert the current update into the rollback table
            cursor.execute("INSERT INTO rollback_data (update_version, update_file) VALUES (?, ?)", (current_update, current_file_data))
            db_connection.commit()
            #print(f"Current update {current_update} moved to rollback data database.")

            # Remove the current file from the install location
            os.remove(current_file_path)
            #print(f"Previous update file removed from install location.")
        except Exception as e:
            #print(f"No previous update file to remove: {e}.") # Expected error if there is no old install file (happens on initialisation)
            pass

        file_path = os.path.join(INSTALL_LOCATION, update_file_name)

        with open(file_path, 'wb') as file:
            file.write(file_data)
        #print(f"File {update_file_name} installed successfully.")

        result = cursor.execute("DELETE FROM update_downloads") # Clears the downloads buffer
        db_connection.commit()
        #print("Update file removed from the download queue.")

        cursor.execute("UPDATE update_information SET update_version = ?, update_install_time = CURRENT_TIMESTAMP WHERE update_entry_id = 1", (update_file_name,)) # Update the version installed and the time
        db_connection.commit()
        #print("Update version updated in the database.")

        db_connection.close()

        # Notifies the server of the new update version installed
        server_host, server_port, ret_val = get_server_information()
        if ret_val == ERROR:
            #print("An error occurred while retrieving the server information.")
            #print("Please check the logs for more details.")
            return ERROR

        selector, connection_socket, ret_val = create_connection(server_host, server_port, selector)
        if ret_val == CONNECTION_INITIATE_ERROR:
            #print("Error: Connection initiation failed.")
            return CONNECTION_INITIATE_ERROR    

        key = selector.get_key(connection_socket)
        
        key.data.data_subtype = UPDATE_VERSION_PUSH
        key.data.outb = str.encode(update_file_name)

        response_event.clear()
        response_event.wait(timeout=None)
        if not response_event.is_set():
            #print("Timeout waiting for server response.")
            return CONNECTION_SERVICE_ERROR

        response_data.clear()  # Clear the response data for the next request
        response_event.clear() # Clear the event for the next request


        return SUCCESS
            
    except Exception as e:
        #print(f"An error occurred: {e}")
        return UPDATE_INSTALL_ERROR

# Gets all informations about itself
def get_all_information() -> typing.Tuple[str, str, str, int]:
    try:
        database, ret_val = get_client_database()
        if ret_val == ERROR:
            #print("An error occurred while retrieving the database name.")
            #print("Please check the logs for more details.")
            return STR_NONE, STR_NONE, STR_NONE, ERROR
        
        db_connection = sqlite3.connect(database)
        cursor = db_connection.cursor()
        # Check if there is an update in the downloads buffer
        downloads_buffer_status = (cursor.execute("SELECT EXISTS (SELECT 1 FROM update_downloads)")).fetchone()[0]
        if downloads_buffer_status == 1:
            update_install_status = UPDATE_IN_DOWNLOADS # Means waiting on an update to be installed
        else:
            update_install_status = UPDATE_INSTALLED

        result = (cursor.execute("SELECT update_version, update_readiness_status FROM update_information WHERE update_entry_id = 1")).fetchone()
        update_version_bytes = str.encode(result[0])
        update_readiness_status = result[1]
        if update_readiness_status == True:
            update_readiness_bytes = UPDATE_READY
        elif update_readiness_status == False:
            update_readiness_bytes = UPDATE_NOT_READY

        db_connection.close()

        return update_version_bytes, update_install_status, update_readiness_bytes, SUCCESS
    
    except Exception as e:
        #print(f"An error occurred: {e}")
        return STR_NONE, STR_NONE, ERROR

# Asks the user which rollback update to install
def rollback_update_install(selector: selectors.SelectSelector, response_event: threading.Event, response_data: dict) -> int:
    try:
        database, ret_val = get_client_database()
        if ret_val == ERROR:
            #print("An error occurred while retrieving the database name.")
            #print("Please check the logs for more details.")
            return STR_NONE, ERROR
        
        db_connection = sqlite3.connect(database)
        cursor = db_connection.cursor()
        result = (cursor.execute("SELECT rollback_entry_id, update_version, update_file FROM rollback_data ORDER BY rollback_entry_id")).fetchall()
        db_connection.close()
        if not result:
            #print("No rollback updates available.")
            return ERROR

        #print("Previous updates to rollback to from the database.")
        #print("-----------------------------------------")
        for row in result:
            #print("Rollback Entry ID: ", row[0])
            #print("Update Version: ", row[1])
            #print("-----------------------------------------")
            pass
        
        rollback_version = int(input("Enter the ID to rollback to: "))

        selected_rollback_version = next((v for v in result if v[0] == rollback_version), None)


        # Queue the rollback as a download and then install it
        ret_val = write_update_file_to_database(selected_rollback_version[1], selected_rollback_version[2]) # File name and data
        if ret_val == SUCCESS:
            #print("Update file written to database successfully.")
            pass
        elif ret_val == DOWNLOAD_UPDATE_ERROR:
            #print("Error: Failed to write update file to database.")
            return DOWNLOAD_UPDATE_ERROR
        else: # ERROR will be from getting database name
            #print("An error occurred while retrieving the database name.")
            #print("Please check the logs for more details.")
            return ERROR
        
        ret_val = install_update(selector, response_event, response_data)
        if ret_val == SUCCESS:
            #print("Update installed successfully.")
            pass
        elif ret_val == CLIENT_NOT_UPDATE_READY_ERROR:
            #print("Error: Client is not ready to receive the update.")
            return CLIENT_NOT_UPDATE_READY_ERROR
        elif ret_val == UPDATE_NOT_AVALIABLE_ERROR:
            #print("Error: There is no update queued for install.")
            return UPDATE_NOT_AVALIABLE_ERROR
        elif ret_val == UPDATE_INSTALL_ERROR:
            #print("Error: There was an error installing the udpate.")
            return UPDATE_INSTALL_ERROR

        return SUCCESS

    except Exception as e:
        #print(f"An error occurred: {e}")
        return ERROR