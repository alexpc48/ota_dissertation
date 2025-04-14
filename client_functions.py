# HEADER FILE

# Libraries
import threading
import platform

from constants import *
from functions import *

# dotenv.load_dotenv(override=True)

# Displays the options menu for client functions
def options_menu() -> str:
    print("\n-------------------------------------------------------------------------------------------")
    print("Options:")
    print("-------------------------------------------------------------------------------------------")
    print("1. Check for an update") # TODO: The server should check if the latest update is the same as the one the client has
    print("2. Download update")
    print("3. Install update") # TODO: Should tell the server the new version number and move the old update to a rollback table in the database
    print("-------------------------------------------------------------------------------------------")
    print("10. Change the update readiness status")
    print("-------------------------------------------------------------------------------------------")
    print("20. Display the update readiness status")
    print("21. Display the update status") # TODO: Check if an update is queud for download or if there is one installed.
    print("22. Display the update version")
    print("-------------------------------------------------------------------------------------------")
    print("30. Rollback update") # TODO: Should display contents of rollback table and ask which version to go to
    print("-------------------------------------------------------------------------------------------")
    print("98. Redisplay the options menu")
    print("99. Exit")
    print("-------------------------------------------------------------------------------------------")

    return input("Enter an option: ")

# Gets the OS type of the client
def get_os_type() -> typing.Tuple[str, int]:
    try:
        os_type = platform.system()
        # if os_type == "Windows":
        #     print("The machine is running Windows.")
        # elif os_type == "Linux":
        #     print("The machine is running Linux.")
        if os_type != "Windows" and os_type != "Linux":
            # print(f"Unknown operating system: {os_type}")
            return STR_NONE, ERROR
        return os_type, SUCCESS
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return STR_NONE, ERROR
    
# Gets which client database to connect to based on the OS type
def get_client_database() -> typing.Tuple[str, int]:
    try:
        os_type, ret_val = get_os_type()
        # if ret_val == SUCCESS:
            # print("OS type retrieved successfully.")
        # else:
        if ret_val == ERROR:
            print("An error occurred while retrieving the OS type.")
            print("Please check the logs for more details.")
            return STR_NONE, ERROR
        
        dotenv.load_dotenv()
        if os_type == "Windows":
            database = os.getenv("WINDOWS_CLIENT_DATABASE")
        elif os_type == "Linux":
            database = os.getenv("LINUX_CLIENT_DATABASE")
        else:
            print(f"Unknown operating system: {os_type}")
            return STR_NONE, ERROR

        return database, SUCCESS

    except Exception as e:
        print(f"An error occurred: {e}")
        return STR_NONE, ERROR

# Gets the server information from the database
def get_server_information() -> typing.Tuple[str, int, int]:
    try:
        database, ret_val = get_client_database()
        if ret_val == ERROR:
            print("An error occurred while retrieving the database name.")
            print("Please check the logs for more details.")
            return ERROR
        
        db_connection = sqlite3.connect(database)
        cursor = db_connection.cursor()
        # Get the server IP and port from the database
        result = (cursor.execute("SELECT server_ip, server_port FROM network_information WHERE network_id = 1")).fetchone()
        server_host, server_port = result[0], result[1]
        print(f"Server IP: {server_host}, Server Port: {server_port}")
        db_connection.close()

        return server_host, server_port, SUCCESS
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return STR_NONE, INT_NONE, ERROR

# Checks the update readiness status in the database
def check_update_readiness_status() -> typing.Tuple[bool, bytes, int]:
    try:
        database, ret_val = get_client_database()
        if ret_val == ERROR:
            print("An error occurred while retrieving the database name.")
            print("Please check the logs for more details.")
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
        print(f"An error occurred: {e}")
        return BOOL_NONE, BYTES_NONE, CHECK_UPDATE_ERROR

# Changes the update readiness status in the database
# Would change automatically based on the vehicle state (i.e., if the vehicle is in motion it would not be available to install an update)
# Manual changing for demonstration purposes
def change_update_readiness() -> int:
    try:
        database, ret_val = get_client_database()
        if ret_val == ERROR:
            print("An error occurred while retrieving the database name.")
            print("Please check the logs for more details.")
            return ERROR

        update_readiness_status, _, ret_val = check_update_readiness_status() # Ignore the bytes value
        print(f"Update readiness status currently: {update_readiness_status}")

        update_readiness_change_value = str(input("Enter a new readiness status (True/False): ")).lower()
        if update_readiness_change_value == str(update_readiness_status):
            print(f"Update readiness status is already set to {update_readiness_status}.")
            return UPDATE_STATUS_REPEAT_ERROR
        elif update_readiness_change_value in ['true', 'false']: # Check if the input is valid
            print("Changing update readiness status ...")
            if update_readiness_change_value == 'true':
                update_readiness_status = int(True)
            elif update_readiness_change_value == 'false':
                update_readiness_status = int(False)
        else:
            print("Invalid input.")
            return ERROR

        db_connection = sqlite3.connect(database)
        cursor = db_connection.cursor()
        cursor.execute("UPDATE update_information SET update_readiness_status = ? WHERE update_entry_id = 1", (update_readiness_status,))
        db_connection.commit()
        db_connection.close()
        print(f"Update readiness status changed to {update_readiness_status}.")
        
        return SUCCESS
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return ERROR

# Connects to the server
# Requests an update check from the server 
# The server will check its latest update against the one it has stored for the client and return the result
def check_for_update(selector: selectors.SelectSelector, response_event: threading.Event, response_data: dict) -> typing.Tuple[bool, int]:
    try:
        server_host, server_port, ret_val = get_server_information()
        if ret_val == ERROR:
            print("An error occurred while retrieving the server information.")
            print("Please check the logs for more details.")
            return BOOL_NONE, ERROR

        selector, connection_socket, ret_val = create_connection(server_host, server_port, selector, response_event)
        if ret_val == CONNECTION_INITIATE_ERROR:
            print("Error: Connection initiation failed.")
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
            print("Timeout waiting for client response.")
            return BOOL_NONE, CONNECTION_SERVICE_ERROR
        
        # Respsonse data is set during service of the connection
        update_avaliable = response_data.get("update_available")
        if update_avaliable == True:
            print("An update is available.")
        elif update_avaliable == False:
            print("There is no new update.")
            return BOOL_NONE, NO_UPDATE_ERROR
        else:
            print("Invalid response from server.")
            return BOOL_NONE, ERROR

        response_data.clear()  # Clear the response data for the next request
        response_event.clear() # Clear the event for the next request

        return update_avaliable, SUCCESS
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return BOOL_NONE, CHECK_UPDATE_ERROR

# Checks if there is an update in the downloads buffer
def check_update_in_downloads_buffer() -> typing.Tuple[int]:
    try:
        database, ret_val = get_client_database()
        if ret_val == ERROR:
            print("An error occurred while retrieving the database name.")
            print("Please check the logs for more details.")
            return ERROR
        
        db_connection = sqlite3.connect(database)
        cursor = db_connection.cursor()
        
        result = (cursor.execute("SELECT EXISTS (SELECT 1 FROM update_downloads)")).fetchone()
        if result[0]:
            # print("An update is already queued for install.")
            # print("Please install the update before downloading a new one.")
            db_connection.close()
            return QUEUED_UPDATE_ERROR

        return SUCCESS
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return ERROR


# Downloads the latest update from the server
def download_update(selector: selectors.SelectSelector, response_event: threading.Event, response_data: dict) -> int:
    try:        
        ret_val = check_update_in_downloads_buffer()
        if ret_val == QUEUED_UPDATE_ERROR:
            print("An update is already queued for install.")
            print("Please install the update before downloading a new one.")
            return QUEUED_UPDATE_ERROR
        elif ret_val == ERROR:
            print("An error occurred while checking the downloads buffer.")
            print("Please check the logs for more details.")
            return ERROR
        
        server_host, server_port, ret_val = get_server_information()
        if ret_val == ERROR:
            print("An error occurred while retrieving the server information.")
            print("Please check the logs for more details.")
            return ERROR

        # update_available, _ = check_for_update(selector, response_event, response_data)
        # if update_available == False:
        #     print("No update available to download.")
        #     return UPDATE_NOT_AVALIABLE

        selector, connection_socket, ret_val = create_connection(server_host, server_port, selector)
        if ret_val == CONNECTION_INITIATE_ERROR:
            print("Error: Connection initiation failed.")
            return CONNECTION_INITIATE_ERROR    

        key = selector.get_key(connection_socket)
        
        key.data.outb = UPDATE_DOWNLOAD_REQUEST

        response_event.clear()
        response_event.wait(timeout=None)
        if not response_event.is_set():
            print("Timeout waiting for server response.")
            return CONNECTION_SERVICE_ERROR

        response_data.clear()  # Clear the response data for the next request
        response_event.clear() # Clear the event for the next request

        return SUCCESS
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return DOWNLOAD_UPDATE_ERROR
        
# Gets the current update version installed
def get_update_version() -> typing.Tuple[str, bytes, int]:
    try:
        database, ret_val = get_client_database()
        if ret_val == ERROR:
            print("An error occurred while retrieving the database name.")
            print("Please check the logs for more details.")
            return STR_NONE, BYTES_NONE, ERROR
        
        db_connection = sqlite3.connect(database)
        cursor = db_connection.cursor()
        update_version = (cursor.execute("SELECT update_version FROM update_information WHERE update_entry_id = 1")).fetchone()[0]
        db_connection.close()
        update_version_bytes = str.encode(update_version)
        return update_version, update_version_bytes, SUCCESS
        
    except Exception as e:
        print(f"An error occurred: {e}")
        return STR_NONE, BYTES_NONE, ERROR
    
# Writes the update file received to the downloads buffer in the database
def write_update_file_to_database(update_file_name: str, file_data: bytes) -> int:
    try:      
        database, ret_val = get_client_database()
        if ret_val == ERROR:
            print("An error occurred while retrieving the database name.")
            print("Please check the logs for more details.")
            return ERROR
        
        db_connection = sqlite3.connect(database)
        cursor = db_connection.cursor()
        cursor.execute("INSERT INTO update_downloads (update_version, update_file) VALUES (?, ?)", (update_file_name, file_data))
        db_connection.commit()
        db_connection.close()

        return SUCCESS
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return DOWNLOAD_UPDATE_ERROR
    
# Installs the update from the downloads buffer in the database
def install_update(selector: selectors.SelectSelector, response_event: threading.Event, response_data: dict) -> int:
    try:
        # Checks if ready to install the update
        update_readiness_status, _, ret_val = check_update_readiness_status()
        if ret_val == SUCCESS and update_readiness_status == False:
                print("Client is not ready to receive the update.")
                return CLIENT_NOT_UPDATE_READY_ERROR
        elif ret_val == ERROR or ret_val == CHECK_UPDATE_ERROR:
            print("An error occurred while checking the update readiness status.")
            print("Please check the logs for more details.")
            return ERROR

        # Check if there is an update queued for download
        ret_val = check_update_in_downloads_buffer()
        if ret_val == QUEUED_UPDATE_ERROR: # Expected result is for an update to be queued
            print("An update is queued for install.")
            print("Please install the update before downloading a new one.")
            return QUEUED_UPDATE_ERROR
        elif ret_val == ERROR:
            print("There is no update queued for install.")
            print("Please download an update before installing.")
            return UPDATE_NOT_AVALIABLE_ERROR
        
        database, ret_val = get_client_database()
        if ret_val == ERROR:
            print("An error occurred while retrieving the database name.")
            print("Please check the logs for more details.")
            return ERROR
        
        db_connection = sqlite3.connect(database)
        cursor = db_connection.cursor()

        result = (cursor.execute("SELECT update_version, update_file FROM update_downloads")).fetchone()
        update_file_name, file_data = result[0], result[1]

        # In reality would install to the vehicle
        # To simulate, it is being installed to a folder location
        file_path = os.path.join("install_location", update_file_name)

        with open(file_path, 'wb') as file:
            file.write(file_data)
        print(f"File {update_file_name} installed successfully.")

        result = cursor.execute("DELETE FROM update_downloads") # Clears the downloads buffer
        db_connection.commit()
        print("Update file removed from the download queue.")

        cursor.execute("UPDATE update_information SET update_version = ? WHERE update_entry_id = 1", (update_file_name,)) # Update the version installed
        db_connection.commit()
        print("Update version updated in the database.")

        db_connection.close()

        return SUCCESS
            
    except Exception as e:
        print(f"An error occurred: {e}")
        return UPDATE_INSTALL_ERROR