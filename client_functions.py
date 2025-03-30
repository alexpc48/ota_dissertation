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
    print("2. Download updates") # TODO: Install the update file to the database
    print("3. Install updates") # TODO: Should also tell the server the new version number
    print("-------------------------------------------------------------------------------------------")
    print("10. Change the update readiness status")
    print("-------------------------------------------------------------------------------------------")
    print("20. Display the update readiness status")
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
        return os_type, SUCCESS
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return ERROR

def get_client_database() -> typing.Tuple[str, int]:
    try:
        os_type, ret_val = get_os_type()
        if ret_val == SUCCESS:
            print("OS type retrieved successfully.")
        else:
            print("An error occurred while retrieving the OS type.")
            print("Please check the logs for more details.")
            return ERROR
        
        dotenv.load_dotenv()
        if os_type == "Windows":
            database = os.getenv("WINDOWS_CLIENT_DATABASE")
        elif os_type == "Linux":
            database = os.getenv("LINUX_CLIENT_DATABASE")
        else:
            print("Unknown operating system.")
            return ERROR

        return database, SUCCESS

    except Exception as e:
        print(f"An error occurred: {e}")
        return ERROR

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
        
        cursor.execute("UPDATE update_information SET update_readiness_status = ? WHERE update_entry_id = 1", (update_readiness_status,))
        db_connection.commit()
        db_connection.close()

        print(f"Update readiness status changed to {update_readiness_status}.")
        return SUCCESS
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return ERROR

# Request an update, if any, from the server
def check_for_update(server_host: str, server_port: int) -> int:
    try:
        print(f"Initiating connection to {server_host}:{server_port} ...")

        connection_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connection_socket.setblocking(False)

        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        data = types.SimpleNamespace(address=(server_host, server_port), inb=b"", outb=b"", connected=False)
        
        # Wait for the connection to complete (blocks all other operations)
        connection_attempts = 0
        while not data.connected:
            err = connection_socket.connect_ex((server_host, server_port)) # Try connecting to the client
            print('[SYN] sent')
            if err == 10056: # Connection made
                print(f"Connection to {server_host}:{server_port} successful.")
                data.connected = True
                print('[SYN-ACK] received')
                break
            elif err == 10035:
                print(f"Connection to {server_host}:{server_port} in progress ...")
                continue
            elif err == 10022: # Tried 5 times to connect then fails
                print("No client found at the specified address.")
                if connection_attempts > 5:
                    print("Connection attempts exceeded. Exiting ...")
                    return CONNECTION_INITIATE_ERROR
                print("Trying again ...")
                time.sleep(5)
                connection_attempts += 1
                continue
            else:
                print(f"Connection to {server_host}:{server_port} failed with error: {errno.errorcode[err]}\n")
                print("Please check the client IP and port.")
                return CONNECTION_INITIATE_ERROR
            
            
        # Register the connection with the selector for read and write events
        selector.register(connection_socket, events, data=data)
                    
        print('Preparing data to send ...')
        data.outb = UPDATE_CHECK_REQUEST
        print('Data ready to send.')

        # Wait for the response to be processed by service_connection
        response_event.clear()
        response_event.wait(timeout=None)  # Wait for up to 10 seconds
        if not response_event.is_set():
            print("Timeout waiting for server response.")
            return CONNECTION_SERVICE_ERROR
        
        if response_data.get("update_available"):
            print("There is an update ready.")
        elif not response_data.get("update_available"):
            print("There is no update ready.")
        update_avaliable = response_data.get("update_available")

        response_data.clear()  # Clear the response data for the next request
        print("Update check request processed successfully.")
        return update_avaliable, SUCCESS
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return CHECK_UPDATE_ERROR

# Download the update from the server (checks first to see if there is an update)
# TODO: Should check if the client is ready to receive the update before downloading it
def download_update(server_host: str, server_port: int) -> int:
    update_available, _ = check_for_update(server_host, server_port)
    if not update_available:
        print("No update available to download.")
        return UPDATE_NOT_AVALIABLE
    
    try:
        print("Checking if the client is ready to receive the update ...")
        db_connection = sqlite3.connect(database)
        cursor = db_connection.cursor()
        update_readiness_status = bool((cursor.execute("SELECT update_readiness_status FROM update_information WHERE update_entry_id = 1")).fetchone()[0])
        
        print(f"Readiness status currently: {update_readiness_status}")

        if update_readiness_status == False:
            print("Client is not ready to receive the update.")
            db_connection.close()
            return CLIENT_NOT_UPDATE_READY_ERROR

        print(f"Initiating connection to {server_host}:{server_port} ...")

        connection_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connection_socket.setblocking(False)

        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        data = types.SimpleNamespace(address=(server_host, server_port), inb=b"", outb=b"", connected=False)
        
        # Wait for the connection to complete (blocks all other operations)
        connection_attempts = 0
        while not data.connected:
            err = connection_socket.connect_ex((server_host, server_port)) # Try connecting to the client
            print('[SYN] sent')
            if err == 10056: # Connection made
                print(f"Connection to {server_host}:{server_port} successful.")
                data.connected = True
                print('[SYN-ACK] received')
                break
            elif err == 10035:
                print(f"Connection to {server_host}:{server_port} in progress ...")
                continue
            elif err == 10022: # Tried 5 times to connect then fails
                print("No client found at the specified address.")
                if connection_attempts > 5:
                    print("Connection attempts exceeded. Exiting ...")
                    return CONNECTION_INITIATE_ERROR
                print("Trying again ...")
                time.sleep(5)
                connection_attempts += 1
                continue
            else:
                print(f"Connection to {server_host}:{server_port} failed with error: {errno.errorcode[err]}\n")
                print("Please check the client IP and port.")
                return CONNECTION_INITIATE_ERROR

        # Register the connection with the selector for read and write events
        selector.register(connection_socket, events, data=data)
                    
        print('Preparing data to send ...')
        data.outb = UPDATE_DOWNLOAD_REQUEST
        print('Data ready to send.')

        # Wait for the response to be processed by service_connection
        response_event.clear()
        response_event.wait(timeout=None)  # Wait for up to 10 seconds
        if not response_event.is_set():
            print("Timeout waiting for server response.")
            return CONNECTION_SERVICE_ERROR

        response_data.clear()  # Clear the response data for the next request
        print("Update downloaded successfully.")
        return SUCCESS
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return DOWNLOAD_UPDATE_ERROR



# # Client checks if it is ready to receive the update
# def check_update_readiness(database) -> int:
#     db_connection = sqlite3.connect(database)
#     cursor = db_connection.cursor()
#     update_readiness_status = bool((cursor.execute("SELECT update_readiness_status FROM update_information WHERE update_entry_id = 1")).fetchone()[0])
#     if update_readiness_status == True:
#         update_readiness_bytes = UPDATE_READY
#     elif update_readiness_status == False:
#         update_readiness_bytes = UPDATE_NOT_READY
#     return update_readiness_status, update_readiness_bytes, SUCCESS



                        db_connection = sqlite3.connect(database)
                    cursor = db_connection.cursor()
                    update_readiness_status = bool((cursor.execute("SELECT update_readiness_status FROM update_information WHERE update_entry_id = 1")).fetchone()[0])
                    db_connection.close()
        

                        case '21':
                    db_connection = sqlite3.connect(database)
                    cursor = db_connection.cursor()
                    update_version = (cursor.execute("SELECT update_version FROM update_information WHERE update_entry_id = 1")).fetchone()[0]
                    db_connection.close()