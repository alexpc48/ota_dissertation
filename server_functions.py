# HEADER FILE

# Libraries
import threading

from constants import *
from functions import *

# Display the options menu for the server
def options_menu() -> str:
    print("\n-------------------------------------------------------------------------------------------")
    print("Options:")
    print("-------------------------------------------------------------------------------------------")
    print("1. Push the latest update to a client")
    print("-------------------------------------------------------------------------------------------")
    print("10. Get a clients update install readiness status")
    print("11. Get a clients update install status")
    print("12. Get a clients installed update version")
    # print("-------------------------------------------------------------------------------------------")
    # print("20. Change the update file")
    print("-------------------------------------------------------------------------------------------")
    print("30. Return all client information")
    print("-------------------------------------------------------------------------------------------")
    print("98. Redisplay the options menu")
    print("99. Exit")
    print("-------------------------------------------------------------------------------------------")

    return input("Enter an option: ")

# Get a list of the clients in the database and their network information
def get_client_network_information() -> typing.Tuple[int, str, str, int, int]:
    try:
        dotenv.load_dotenv()
        database = os.getenv("SERVER_DATABASE")

        db_connection = sqlite3.connect(database)
        cursor = db_connection.cursor()
        result = (cursor.execute("SELECT vehicles_entry_id, vehicle_id, vehicle_ip, vehicle_port FROM vehicles ORDER BY vehicles_entry_id")).fetchall()
        db_connection.close()

        print("Vehicle entries in the database.")
        print("-----------------------------------------")
        for row in result:
            print("Vehicle Entry ID: ", row[0])
            print("Vehicle ID: ", row[1])
            print("Vehicle IP: ", row[2])
            print("Vehicle Port: ", row[3])
            print("-----------------------------------------")
        
        vehicle_id_input = int(input("Enter the vehicle ID to connect with: "))

        # AI help for next() function
        selected_vehicle = next((v for v in result if v[0] == vehicle_id_input), None)

        identifier = selected_vehicle[1]
        client_host = selected_vehicle[2]
        client_port = selected_vehicle[3]

        return vehicle_id_input, identifier, client_host, client_port, SUCCESS

    except Exception as e:
        print(f"An error occurred: {e}")
        return INT_NONE, STR_NONE, STR_NONE, INT_NONE, ERROR

# Requests the clients update version from the client
def get_client_update_version(selector: selectors.SelectSelector, response_event: threading.Event, response_data: dict) -> typing.Tuple[str, str, int]:
    try:
        vehicle_entry_id, identifier, client_host, client_port, ret_val = get_client_network_information()
        if ret_val == ERROR:
            print("An error occurred while retrieving the client network information.")
            return STR_NONE, STR_NONE, ERROR
        
        selector, connection_socket, ret_val = create_connection(client_host, client_port, selector)
        if ret_val == CONNECTION_INITIATE_ERROR:
            print("Error: Connection initiation failed.")
            return identifier, STR_NONE, CONNECTION_INITIATE_ERROR

        key = selector.get_key(connection_socket)

        key.data.identifier = identifier

        key.data.outb = UPDATE_VERSION_REQUEST

        response_event.clear()
        response_event.wait(timeout=None)
        if not response_event.is_set():
            print("Timeout waiting for client response.")
            return STR_NONE, STR_NONE, CONNECTION_SERVICE_ERROR
        
        client_update_version = response_data.get("update_version")
        print(f"Client update version: {client_update_version}")

        dotenv.load_dotenv()
        database = os.getenv("SERVER_DATABASE")
        db_connection = sqlite3.connect(database)
        cursor = db_connection.cursor()
        # Gets the latest update file from the database
        latest_update_version = (cursor.execute("SELECT updates.update_version FROM vehicles JOIN updates ON vehicles.update_id = updates.update_id WHERE vehicles.vehicles_entry_id = ?;", (vehicle_entry_id,))).fetchone()[0]
        # Updates poll time and version number
        client_update_id = cursor.execute("SELECT update_id FROM updates WHERE update_version = ?", (client_update_version,)).fetchone()[0]
        cursor.execute("UPDATE vehicles SET update_id = ?, last_poll_time = CURRENT_TIMESTAMP WHERE vehicles_entry_id = ?;", (client_update_id, vehicle_entry_id)) # Uses the current timestamp to determine when version number was retrieved
        db_connection.commit()
        db_connection.close()

        if latest_update_version == client_update_version:
            print("Client is up to date.")
        else:
            print("Client is not up to date.")
            print("Please update the client.")
        
        response_data.clear()  # Clear the response data for the next request
        response_event.clear() # Clear the event for the next request

        return identifier, client_update_version, SUCCESS
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return STR_NONE, STR_NONE, ERROR

# Gets the update readiness status from the client
def get_client_update_readiness_status(selector: selectors.SelectSelector, response_event: threading.Event, response_data: dict) -> typing.Tuple[bool, int]:
    try:
        vehicle_entry_id, identifier, client_host, client_port, ret_val = get_client_network_information()
        if ret_val == ERROR:
            print("An error occurred while retrieving the client network information.")
            return BOOL_NONE, ERROR
        
        selector, connection_socket, ret_val = create_connection(client_host, client_port, selector)
        if ret_val == CONNECTION_INITIATE_ERROR:
            print("Error: Connection initiation failed.")
            return BOOL_NONE, CONNECTION_INITIATE_ERROR

        key = selector.get_key(connection_socket)

        key.data.identifier = identifier

        key.data.outb = UPDATE_READINESS_STATUS_REQUEST

        response_event.clear()
        response_event.wait(timeout=None)
        if not response_event.is_set():
            print("Timeout waiting for client response.")
            return BOOL_NONE, CONNECTION_SERVICE_ERROR
        
        update_readiness = response_data.get('update_readiness')

        dotenv.load_dotenv()
        database = os.getenv("SERVER_DATABASE")
        db_connection = sqlite3.connect(database)
        cursor = db_connection.cursor()
        # Update poll time
        cursor.execute("UPDATE vehicles SET last_poll_time = CURRENT_TIMESTAMP WHERE vehicles_entry_id = ?;", (vehicle_entry_id,)) # Uses the current timestamp to determine when version number was retrieved
        db_connection.commit()
        db_connection.close()

        if update_readiness == True:
            print("Client is ready to install the update.")
        elif update_readiness == False:
            print("Client is not ready to install the update.")
            return update_readiness, CLIENT_NOT_UPDATE_READY_ERROR
        
        response_data.clear()  # Clear the response data for the next request
        response_event.clear() # Clear the event for the next request

        return update_readiness, SUCCESS
        
    except Exception as e:
        print(f"An error occurred: {e}")
        return BOOL_NONE, ERROR
    
# Pushes an update to the client
# Example when a new update comes out, the server will push the update to the client
def push_update(selector: selectors.SelectSelector, response_event: threading.Event, response_data: dict) -> int:
    try:
        _, identifier, client_host, client_port, ret_val = get_client_network_information()
        if ret_val == ERROR:
            print("An error occurred while retrieving the client network information.")
            return ERROR
        
        print("Checking if the client is up to date ...")
        dotenv.load_dotenv()
        database = os.getenv("SERVER_DATABASE")
        db_connection = sqlite3.connect(database)
        cursor = db_connection.cursor()
        latest_update_version = (cursor.execute("SELECT update_version FROM updates ORDER BY update_id DESC LIMIT 1")).fetchone()[0] # Get the latest update version from the database
        client_stored_update_version = (cursor.execute("SELECT updates.update_version FROM vehicles JOIN updates ON vehicles.update_id = updates.update_id WHERE vehicles.vehicle_id = ?", (identifier,))).fetchone()[0] # Get the client's current update version
        db_connection.close()

        # Compare the versions
        if client_stored_update_version == latest_update_version:
            print(f"Client {identifier} is already up to date with version {latest_update_version}.")
            return CLIENT_UP_TO_DATE_ERROR
        else:
            print(f"Client is not up to date. Pushing update ...")
        
        selector, connection_socket, ret_val = create_connection(client_host, client_port, selector)
        if ret_val == CONNECTION_INITIATE_ERROR:
            print("Error: Connection initiation failed.")
            return CONNECTION_INITIATE_ERROR

        key = selector.get_key(connection_socket)

        key.data.identifier = identifier

        key.data.file_name, file_data, _ = get_update_file() # Use socket for global file name access
        key.data.data_subtype = UPDATE_FILE
        key.data.outb = file_data

        response_event.clear()
        response_event.wait(timeout=None)
        if not response_event.is_set():
            print("Timeout waiting for client response.")
            return CONNECTION_SERVICE_ERROR
        
        response_data.clear()  # Clear the response data for the next request
        response_event.clear() # Clear the event for the next request

        return SUCCESS
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return ERROR

# Gets the latest update file from the database
def get_update_file() -> typing.Tuple[bytes, bytes, int]:
    try:
        dotenv.load_dotenv()
        database = os.getenv("SERVER_DATABASE")
        db_connection = sqlite3.connect(database)
        cursor = db_connection.cursor()
        # Gets the latest update file from the database
        update_version, update_file = (cursor.execute("SELECT update_version, update_file FROM updates ORDER BY update_id DESC LIMIT 1")).fetchone()
        db_connection.close()
        return str.encode(update_version), update_file, SUCCESS
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return STR_NONE, BYTES_NONE, ERROR

# Compares the latest update version against the one stored for the client
def check_for_updates(identifier: str) -> typing.Tuple[bool, bytes]:

    dotenv.load_dotenv()
    database = os.getenv("SERVER_DATABASE")
    db_connection = sqlite3.connect(database)
    cursor = db_connection.cursor()
    latest_update_version = cursor.execute("SELECT update_version FROM updates ORDER BY update_id DESC LIMIT 1").fetchone()[0]
    client_update_version = cursor.execute("SELECT updates.update_version FROM vehicles JOIN updates ON vehicles.update_id = updates.update_id WHERE vehicles.vehicle_id = ?", (identifier,)).fetchone()[0]
    db_connection.close()

    # Compare the versions
    if client_update_version == latest_update_version:
        print("Client is up to date.")
        update_available = False
        update_available_bytes = UPDATE_NOT_AVALIABLE
    else:
        print("Client is not up to date.")
        update_available = True
        update_available_bytes = UPDATE_AVALIABLE

    return update_available, update_available_bytes

# Polls all available clients for an information table
# Gets their update version, update readiness status, and update install status (file name = dynamic length, readiness status is 4 bytes, update intstall status = 5 bytes)
def poll_all_clients(selector: selectors.SelectSelector, response_event: threading.Event, response_data: dict) -> typing.Tuple[dict, int]:
    try:
        dotenv.load_dotenv()
        database = os.getenv("SERVER_DATABASE")
        db_connection = sqlite3.connect(database)
        cursor = db_connection.cursor()
        # Retrieve all client network information from the database
        clients = cursor.execute("SELECT vehicle_id, vehicle_ip, vehicle_port FROM vehicles").fetchall()
        db_connection.close()

        client_poll_information = {}
        # Go through each client and poll them for information
        for client in clients:
            identifier, client_host, client_port = client
            print(f"Polling client at {client_host}:{client_port} ...")
            selector, connection_socket, ret_val = create_connection(client_host, client_port, selector)
            if ret_val == CONNECTION_INITIATE_ERROR: # Means client is not online, so return current information stored and timestamp
                print("Error: Connection initiation failed. Client is not online.")
                db_connection = sqlite3.connect(database)
                cursor = db_connection.cursor()
                # Retrieve update version and readiness status from the database for the given identifier
                result = cursor.execute("SELECT update_readiness_status, update_install_status updates.update_version FROM vehicles JOIN updates ON vehicles.update_id = updates.update_id WHERE vehicles.vehicle_id = ?", (identifier,)).fetchone()
                update_readiness_status, update_install_status, update_version = result[0], result[1], result[2]
                last_poll_time = cursor.execute("SELECT last_poll_time FROM vehicles WHERE vehicle_id = ?", (identifier,)).fetchone()[0]
                db_connection.close()
                # Convert to datetime object
                last_poll_time = datetime.datetime.strptime(last_poll_time, "%Y-%m-%d %H:%M:%S").strftime("%d-%m-%Y %H:%M:%S") # Poll time is in the wrong format (uses CURRENT_TIMESTAMP), so reformat

                client_poll_information[identifier] = {
                "update_version": update_version,
                "update_install_status": update_install_status,
                "update_readiness_status": update_readiness_status,
                "last_poll_time": last_poll_time
                }
                
                break

            key = selector.get_key(connection_socket)
            key.data.identifier = identifier

            key.data.data_subtype = ALL_INFORMATION
            key.data.outb = ALL_INFORMATION_REQUEST

            response_event.clear()
            response_event.wait(timeout=None)
            if not response_event.is_set():
                print("Timeout waiting for client response.")
                return CONNECTION_SERVICE_ERROR
        
            update_version, update_install_status, update_readiness_status = response_data.get("all_information")

            client_poll_information[identifier] = {
                "update_version": update_version,
                "update_install_status": update_install_status,
                "update_readiness_status": update_readiness_status,
                "last_poll_time": datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")
            }
        
        # print(client_poll_information)
        # print(type(client_poll_information))
            
        response_data.clear()  # Clear the response data for the next request
        response_event.clear() # Clear the event for the next request

        return client_poll_information, SUCCESS
                
    except Exception as e:
        print(f"An error occurred: {e}")
        return None, ERROR

# Gets the clients current update install status
def get_client_update_install_status(selector: selectors.SelectSelector, response_event: threading.Event, response_data: dict) -> typing.Tuple[str, int]:
    try:
        _, identifier, client_host, client_port, ret_val = get_client_network_information()
        if ret_val == ERROR:
            print("An error occurred while retrieving the client network information.")
            return STR_NONE, ERROR
        
        selector, connection_socket, ret_val = create_connection(client_host, client_port, selector)
        if ret_val == CONNECTION_INITIATE_ERROR:
            print("Error: Connection initiation failed.")
            return STR_NONE, CONNECTION_INITIATE_ERROR

        key = selector.get_key(connection_socket)

        key.data.identifier = identifier

        key.data.outb = INSTALL_STATUS_REQUEST

        response_event.clear()
        response_event.wait(timeout=None)
        if not response_event.is_set():
            print("Timeout waiting for client response.")
            return STR_NONE, CONNECTION_SERVICE_ERROR
        
        update_install_status = response_data.get('update_install_status')

        if update_install_status == UPDATE_INSTALLED:
            update_install_status_bool = True # True as all updates are installed
        elif update_install_status == UPDATE_IN_DOWNLOADS:
            update_install_status_bool = False

        # Add value to database and update last poll time
        dotenv.load_dotenv()
        database = os.getenv("SERVER_DATABASE")
        db_connection = sqlite3.connect(database)
        cursor = db_connection.cursor()
        cursor.execute("UPDATE vehicles SET update_install_status = ?, last_poll_time = CURRENT_TIMESTAMP WHERE vehicle_id = ?;", (update_install_status_bool, identifier))
        db_connection.commit()
        db_connection.close()
            

        response_data.clear()  # Clear the response data for the next request
        response_event.clear() # Clear the event for the next request

        return update_install_status, SUCCESS
        
    except Exception as e:
        print(f"An error occurred: {e}")
        return BYTES_NONE, ERROR

# Adds the recevied update verison when it is pushed to the database
def add_update_version_to_database(identifier: str, version_number: str) -> int:
    try:
        dotenv.load_dotenv()
        database = os.getenv("SERVER_DATABASE")
        db_connection = sqlite3.connect(database)
        cursor = db_connection.cursor()
        update_id = cursor.execute("SELECT update_id FROM updates WHERE update_version = ?", (version_number,)).fetchone()[0] # Gets the corresponding update ID for the version number
        if not update_id:
            print(f"Error: Update version {version_number} does not exist in the database.")
            return ERROR
        cursor.execute("UPDATE vehicles SET update_id = ?, last_poll_time = CURRENT_TIMESTAMP WHERE vehicle_id = ?", (update_id, identifier))
        db_connection.commit()
        db_connection.close()
        
        print("Database updated successfully.")
        return SUCCESS

    except Exception as e:
        print(f"An error occurred: {e}")
        return ERROR