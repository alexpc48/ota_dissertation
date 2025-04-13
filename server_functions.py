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
    print("1. Push the latest update to the client") # TODO: Check first if the client already has the update
    print("-------------------------------------------------------------------------------------------")
    print("10. Get the client update readiness status") # TODO: Remove maybe - not that relevant information
    print("11. Get the client update status") # TODO: Check if the update has been installed, failed, behind, etc.
    print("12. Get the client update version")
    print("-------------------------------------------------------------------------------------------")
    print("20. Change the update file") # TODO
    print("-------------------------------------------------------------------------------------------")
    print("30. Return all client information") # TODO: Returns information polled from clients, or the information taken from the database if client is not up
    print("-------------------------------------------------------------------------------------------")
    print("40. Change security status") # Changes if security is enabled or not (TESTING ONLY - would not be in a real application)
    print("-------------------------------------------------------------------------------------------")
    print("98. Redisplay the options menu")
    print("99. Exit")
    print("-------------------------------------------------------------------------------------------")

    return input("Enter an option: ")

# Changes security status
def change_security_status() -> int:
    try:
        dotenv.load_dotenv(override=True) # Refreshes for the security mode variable
        print(f"Current security status: {os.getenv('SECURITY_MODE')}")
        new_security_mode = input("Enter a new security status (1 = Secure, 0 = Insecure): ")

        # Re-write the .env file with the new security mode
        # TESTIG ONLY
        # Would not be in a real application
        # Used so application does not need to be recompiled to change security mode
        with open('.env', 'r') as file:
            lines = file.readlines()
        with open('.env', 'w') as file:
            for line in lines:
                if 'SECURITY_MODE' in line:
                    file.write(f'SECURITY_MODE = {new_security_mode}\n')
                else:
                    file.write(line)

        return SUCCESS

    except Exception as e:
        print(f"An error occurred: {e}")
        return ERROR

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
        for result in result:
            print("Vehicle Entry ID: ", result[0])
            print("Vehicle ID: ", result[1])
            print("Vehicle IP: ", result[2])
            print("Vehicle Port: ", result[3])
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
        return INT_NONE, STR_NONE, INT_NONE, ERROR

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
        client_update_id = cursor.execute("SELECT update_id FROM updates WHERE update_version = ?", (client_update_version,)).fetchone()
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

        return STR_NONE, client_update_version, SUCCESS
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return STR_NONE, STR_NONE, ERROR

# Gets the update readiness status from the client
# def get_client_update_readiness_status(selector: selectors.SelectSelector, response_event: threading.Event, response_data: dict) -> typing.Tuple[bool, int]:
#     try:
#         vehicle_entry_id, identifier, client_host, client_port, ret_val = get_client_network_information()
#         if ret_val == ERROR:
#             print("An error occurred while retrieving the client network information.")
#             return BOOL_NONE, ERROR
        
#         selector, connection_socket, ret_val = create_connection(client_host, client_port, selector)
#         if ret_val == CONNECTION_INITIATE_ERROR:
#             print("Error: Connection initiation failed.")
#             return BOOL_NONE, CONNECTION_INITIATE_ERROR

#         key = selector.get_key(connection_socket)

#         key.data.identifier = identifier

#         key.data.outb = UPDATE_READINESS_STATUS_REQUEST

#         response_event.clear()
#         response_event.wait(timeout=None)
#         if not response_event.is_set():
#             print("Timeout waiting for client response.")
#             return BOOL_NONE, CONNECTION_SERVICE_ERROR
        
#         update_readiness = response_data.get('update_readiness')

#         dotenv.load_dotenv()
#         database = os.getenv("SERVER_DATABASE")
#         db_connection = sqlite3.connect(database)
#         cursor = db_connection.cursor()
#         # Update poll time
#         cursor.execute("UPDATE vehicles SET last_poll_time = CURRENT_TIMESTAMP WHERE vehicles_entry_id = ?;", (vehicle_entry_id,)) # Uses the current timestamp to determine when version number was retrieved
#         db_connection.commit()
#         db_connection.close()

#         if update_readiness == True:
#             print("Client is ready to install the update.")
#         elif update_readiness == False:
#             print("Client is not ready to install the update.")
#             return update_readiness, CLIENT_NOT_UPDATE_READY_ERROR
        
#         response_data.clear()  # Clear the response data for the next request
#         response_event.clear() # Clear the event for the next request

#         return update_readiness, SUCCESS
        
#     except Exception as e:
#         print(f"An error occurred: {e}")
#         return BOOL_NONE, ERROR
    
# Pushes an update to the client
# Example when a new update comes out, the server will push the update to the client
def push_update(selector: selectors.SelectSelector, response_event: threading.Event, response_data: dict) -> int:
    try:
        _, identifier, client_host, client_port, ret_val = get_client_network_information()
        if ret_val == ERROR:
            print("An error occurred while retrieving the client network information.")
            return ERROR
        
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
    
# TODO: Should check if the latest update is installed or not on the client (compaing server local db)
def check_for_updates() -> typing.Tuple[bool, bytes]:
    if True:
        update_available = True
        update_available_bytes = UPDATE_AVALIABLE
    else:
        update_available = False
        update_available_bytes = UPDATE_NOT_AVALIABLE
    return update_available, update_available_bytes