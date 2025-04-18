# HEADER FILE

# Libraries
import random
import socket
import typing
import selectors
import threading
import os
import types
import errno
import time
import sqlite3
import dotenv
import platform
from constants import *
from functions import *

def options_menu() -> str:
    print("\n-------------------------------------------------------------------------------------------")
    print("Options:")
    print("-------------------------------------------------------------------------------------------")
    print("1. Check for an update")
    print("2. Download updates")
    print("3. Install updates") # TODO: Should also tell the server the new version number
    print("-------------------------------------------------------------------------------------------")
    print("10. Change the update readiness status")
    print("-------------------------------------------------------------------------------------------")
    print("20. Display the update readiness status")
    # print("21. Display the update status") # TODO
    print("21. Display the update version")
    print("-------------------------------------------------------------------------------------------")
    print("98. Redisplay the options menu")
    print("-------------------------------------------------------------------------------------------")
    print("99. Exit")
    print("-------------------------------------------------------------------------------------------")

    return input("Enter an option: ")

def get_os_type() -> typing.Tuple[str, int]:
    try:
        os_type = platform.system()
        if os_type == "Windows":
            print("The machine is running Windows.")
        elif os_type == "Linux":
            print("The machine is running Linux.")
        else:
            print(f"Unknown operating system: {os_type}")
            return ERROR
        return os_type, SUCCESS
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return STR_NONE, ERROR

def get_client_database() -> typing.Tuple[str, int]:
    try:
        os_type, ret_val = get_os_type()
        if ret_val == SUCCESS:
            print("OS type retrieved successfully.")
        else:
            print("An error occurred while retrieving the OS type.")
            print("Please check the logs for more details.")
            return '', ERROR
        
        dotenv.load_dotenv()
        if os_type == "Windows":
            database = os.getenv("WINDOWS_CLIENT_DATABASE")
        elif os_type == "Linux":
            database = os.getenv("LINUX_CLIENT_DATABASE")
        else:
            print("Unknown operating system.")
            return '', ERROR

        return database, SUCCESS

    except Exception as e:
        print(f"An error occurred: {e}")
        return '', ERROR

def change_update_readiness() -> int:
    try:
        database, ret_val = get_client_database()
        if ret_val == SUCCESS:
            print("Database name retrieved successfully.")
        else:
            print("An error occurred while retrieving the database name.")
            print("Please check the logs for more details.")
            return ERROR

        db_connection = sqlite3.connect(database)
        cursor = db_connection.cursor()
        update_readiness_status = bool((cursor.execute("SELECT update_readiness_status FROM update_information WHERE update_entry_id = 1")).fetchone()[0])
        db_connection.close()

        print(f"Readiness status currently: {update_readiness_status}")
        update_readiness_change_value = str(input("Enter new readiness status (True/False): "))
        if update_readiness_change_value == str(update_readiness_status):
            print(f"Update readiness status is already set to {update_readiness_status}.")
            return UPDATE_STATUS_REPEAT_ERROR
        elif update_readiness_change_value in ['True', 'False']: # Check if the input is valid
            print("Changing update readiness status ...")
        else:
            print("Invalid input.")
            return ERROR

        if update_readiness_change_value == 'True':
            update_readiness_status = int(True)
        elif update_readiness_change_value == 'False':
            update_readiness_status = int(False)
        
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

# TODO: Store the value in the database and have it so the server can say there is a new update and the client updates its database
def check_for_update(selector: selectors.SelectSelector, response_event: threading.Event, response_data: dict) -> typing.Tuple[bool, int]:
    try:
        database, ret_val = get_client_database()
        if ret_val == SUCCESS:
            print("Database name retrieved successfully.")
        else:
            print("An error occurred while retrieving the database name.")
            print("Please check the logs for more details.")
            return None, ERROR
        
        # Get the server IP and port from the database
        db_connection = sqlite3.connect(database)
        cursor = db_connection.cursor()
        result = (cursor.execute("SELECT server_ip, server_port FROM network_information WHERE network_id = 1")).fetchone()
        db_connection.close()
        server_host, server_port = result[0], result[1]

        selector, connection_socket, ret_val = create_connection(server_host, server_port, selector)
        if ret_val == SUCCESS:
            print("Connection to client established.")
        elif ret_val == CONNECTION_INITIATE_ERROR:
            print("Error: Connection initiation failed.")
            return None, CONNECTION_INITIATE_ERROR
        else:
            print("An error occurred while establishing the connection.")
            return None, ERROR
        
        key = selector.get_key(connection_socket)

        print('Preparing data to send ...')
        key.data.outb = UPDATE_CHECK_REQUEST
        print('Data ready to send.')

        response_event.clear()
        response_event.wait(timeout=None)
        if not response_event.is_set():
            print("Timeout waiting for client response.")
            return None, CONNECTION_SERVICE_ERROR
        
        update_avaliable = response_data.get("update_available")
        if update_avaliable == False:
            print("There is no update ready.")
            return None, NO_UPDATE_ERROR

        response_data.clear()  # Clear the response data for the next request
        response_event.clear() # Clear the event for the next request
        print("Update check request processed successfully.")
        return update_avaliable, SUCCESS
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return None, CHECK_UPDATE_ERROR

def check_update_readiness_status() -> typing.Tuple[bool, bytes, int]:
    try:
        database, ret_val = get_client_database()
        if ret_val == SUCCESS:
            print("Database name retrieved successfully.")
        else:
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

# TODO: Needs to check if the update is not already installed or not (i.e., compare version number)
def download_update(selector: selectors.SelectSelector, response_event: threading.Event, response_data: dict) -> int:
    try:
        database, ret_val = get_client_database()
        if ret_val == SUCCESS:
            print("Database name retrieved successfully.")
        else:
            print("An error occurred while retrieving the database name.")
            print("Please check the logs for more details.")
            return ERROR
        
        # Get the server IP and port from the database
        db_connection = sqlite3.connect(database)
        cursor = db_connection.cursor()

        # Check if there is already an update queued for download
        result = (cursor.execute("SELECT EXISTS (SELECT 1 FROM update_downloads)")).fetchone()
        if result[0]:
            print("An update is already queued for download.")
            db_connection.close()
            return QUEUED_UPDATE_ERROR
        
        result = (cursor.execute("SELECT server_ip, server_port FROM network_information WHERE network_id = 1")).fetchone()
        db_connection.close()
        server_host, server_port = result[0], result[1]

        update_available, _ = check_for_update(selector, response_event, response_data)
        if update_available == False:
            print("No update available to download.")
            return UPDATE_NOT_AVALIABLE

        selector, connection_socket, ret_val = create_connection(server_host, server_port, selector)
        if ret_val == SUCCESS:
            print("Connection to server established.")
        elif ret_val == CONNECTION_INITIATE_ERROR:
            print("Error: Connection initiation failed.")
            return CONNECTION_INITIATE_ERROR
        else:
            print("An error occurred while establishing the connection.")
            return ERROR        

        key = selector.get_key(connection_socket)
        
        print('Preparing data to send ...')
        key.data.outb = UPDATE_DOWNLOAD_REQUEST
        print('Data ready to send.')

        response_event.clear()
        response_event.wait(timeout=None)
        if not response_event.is_set():
            print("Timeout waiting for server response.")
            return CONNECTION_SERVICE_ERROR

        response_data.clear()  # Clear the response data for the next request
        response_event.clear() # Clear the event for the next request
        print("Update downloaded successfully.")
        return SUCCESS
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return DOWNLOAD_UPDATE_ERROR
        
def get_update_version() -> typing.Tuple[str, bytes, int]:
    try:
        database, ret_val = get_client_database()
        if ret_val == SUCCESS:
            print("Database name retrieved successfully.")
        else:
            print("An error occurred while retrieving the database name.")
            print("Please check the logs for more details.")
            return '', ERROR
        
        db_connection = sqlite3.connect(database)
        cursor = db_connection.cursor()
        update_version = (cursor.execute("SELECT update_version FROM update_information WHERE update_entry_id = 1")).fetchone()[0]
        print(update_version)
        db_connection.close()
        update_version_bytes = str.encode(update_version)
        return update_version, update_version_bytes, SUCCESS
        
    except Exception as e:
        print(f"An error occurred: {e}")
        return STR_NONE, BYTES_NONE, ERROR
    
def write_update_file_to_database(update_file_name: str, file_data: bytes) -> int:
    try:      
        database, ret_val = get_client_database()
        if ret_val == SUCCESS:
            print("Database name retrieved successfully.")
        else:
            print("An error occurred while retrieving the database name.")
            print("Please check the logs for more details.")
            return ERROR
        
        db_connection = sqlite3.connect(database)
        cursor = db_connection.cursor()
        print(type(update_file_name))
        cursor.execute('''INSERT INTO update_downloads (update_version, update_file)
                    VALUES (?, ?)''',
                    (update_file_name, file_data))
        db_connection.commit()
        db_connection.close()
        return SUCCESS
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return DOWNLOAD_UPDATE_ERROR
    
def install_update(selector: selectors.SelectSelector, response_event: threading.Event, response_data: dict) -> int:
    try:
        # Check if ready to install the update
        update_readiness_status, _, ret_val = check_update_readiness_status()
        if ret_val == SUCCESS:
            print(f"Readiness status currently: {update_readiness_status}")
            if update_readiness_status == False:
                print("Client is not ready to receive the update.")
                return CLIENT_NOT_UPDATE_READY_ERROR
            
        database, ret_val = get_client_database()
        if ret_val == SUCCESS:
            print("Database name retrieved successfully.")
        else:
            print("An error occurred while retrieving the database name.")
            print("Please check the logs for more details.")
            return STR_NONE, ERROR
        
        db_connection = sqlite3.connect(database)
        cursor = db_connection.cursor()

        # Check if there is an update queued for download
        result = (cursor.execute("SELECT EXISTS (SELECT 1 FROM update_downloads)")).fetchone()
        if not result[0]: # No update
            print("There is no update available for install.")
            db_connection.close()
            return UPDATE_NOT_AVALIABLE_ERROR
        
        result = (cursor.execute("SELECT update_version, update_file FROM update_downloads")).fetchone()
        update_file_name = result[0]
        file_data = result[1]
        print(update_file_name)

        file_path = os.path.join("install_location", update_file_name)

        with open(file_path, 'wb') as file:
            file.write(file_data)
        print(f"File {update_file_name} installed successfully.")

        result = cursor.execute("DELETE FROM update_downloads")
        db_connection.commit()
        print("Update file removed from the download queue.")


        cursor.execute("UPDATE update_information SET update_version = ? WHERE update_entry_id = 1", (update_file_name,)) # Update the version installed
        db_connection.commit()
        db_connection.close()
        print("Update version updated in the database.")
        

        # database, ret_val = get_client_database()
        # if ret_val == SUCCESS:
        #     print("Database name retrieved successfully.")
        # else:
        #     print("An error occurred while retrieving the database name.")
        #     print("Please check the logs for more details.")
        #     return ERROR
        
        # # Get the server IP and port from the database
        # db_connection = sqlite3.connect(database)
        # cursor = db_connection.cursor()

        # # Check if there is already an update queued for download
        # result = (cursor.execute("SELECT EXISTS (SELECT 1 FROM update_downloads)")).fetchone()
        # if result[0]:
        #     print("An update is already queued for download.")
        #     db_connection.close()
        #     return QUEUED_UPDATE_ERROR
        
        # result = (cursor.execute("SELECT server_ip, server_port FROM network_information WHERE network_id = 1")).fetchone()
        # db_connection.close()
        # server_host, server_port = result[0], result[1]

        # selector, connection_socket, ret_val = create_connection(server_host, server_port, selector)
        # if ret_val == SUCCESS:
        #     print("Connection to server established.")
        # elif ret_val == CONNECTION_INITIATE_ERROR:
        #     print("Error: Connection initiation failed.")
        #     return CONNECTION_INITIATE_ERROR
        # else:
        #     print("An error occurred while establishing the connection.")
        #     return ERROR        

        # key = selector.get_key(connection_socket)
        
        # print('Preparing data to send ...')
        # key.data.data_subtype = UPDATE_VERSION_PUSH
        # key.data.outb = str.encode(update_file_name)
        # print('Data ready to send.')

        # response_event.clear()
        # response_event.wait(timeout=None)
        # if not response_event.is_set():
        #     print("Timeout waiting for server response.")
        #     return CONNECTION_SERVICE_ERROR

        # response_data.clear()  # Clear the response data for the next request
        # response_event.clear() # Clear the event for the next request
        # print("Sending new update version to the server")
    
        print("Update installed successfully.")
        return SUCCESS
            
    except Exception as e:
        print(f"An error occurred: {e}")
        return UPDATE_INSTALL_ERROR