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
from constants import *
from functions import *

def options_menu() -> str:
    print("\n-------------------------------------------------------------------------------------------")
    print("Options:")
    print("-------------------------------------------------------------------------------------------")
    print("1. Push the latest update to the client")
    print("-------------------------------------------------------------------------------------------")
    print("10. Get the client update readiness status")
    print("11. Get the client update status") # TODO: Check if the update has been installed, failed, behind, etc.
    print("12. Get the client update version")
    print("-------------------------------------------------------------------------------------------")
    print("20. Change the update file") # TODO
    print("-------------------------------------------------------------------------------------------")
    print("30. Return all client information") # TODO: Returns information polled from clients, or the information taken from the database if client is not up
    print("-------------------------------------------------------------------------------------------")
    print("98. Redisplay the options menu")
    print("99. Exit")
    print("-------------------------------------------------------------------------------------------")

    return input("Enter an option: ")

def get_client_network_information() -> typing.Tuple[int, str, int, int]:
    try:
        dotenv.load_dotenv()
        database = os.getenv("SERVER_DATABASE") # Not using a default database

        db_connection = sqlite3.connect(database)
        cursor = db_connection.cursor()
        query_result = (cursor.execute("SELECT vehicles_entry_id, vehicle_id, vehicle_ip, vehicle_port FROM vehicles ORDER BY vehicles_entry_id")).fetchall()
        db_connection.close()

        print("Vehicle entries in the database.")
        for result in query_result:
            print("Vehicle Entry ID: ", result[0])
            print("Vehicle ID: ", result[1])
            print("Vehicle IP: ", result[2])
            print("Vehicle Port: ", result[3])
        
        vehicle_id_input = int(input("Enter the vehicle ID to connect with: "))

        # AI help for next() function
        selected_vehicle = next((v for v in query_result if v[0] == vehicle_id_input), None)

        client_host = selected_vehicle[2]
        client_port = selected_vehicle[3]

        return vehicle_id_input, client_host, client_port, SUCCESS

    except Exception as e:
        print(f"An error occurred: {e}")
        return INT_NONE, STR_NONE, INT_NONE, ERROR

def get_client_update_version(selector: selectors.SelectSelector, response_event: threading.Event, response_data: dict) -> int:
    try:
        vehicle_entry_id, client_host, client_port, ret_val = get_client_network_information()
        if ret_val == SUCCESS:
            print("Retreived client information.")
        else:
            print("An error occurred.")
            return ERROR
        
        selector, connection_socket, ret_val = create_connection(client_host, client_port, selector)
        if ret_val == SUCCESS:
            print("Connection to client established.")
        elif ret_val == CONNECTION_INITIATE_ERROR:
            print("Error: Connection initiation failed.")
            return CONNECTION_INITIATE_ERROR
        else:
            print("An error occurred.")
            return ERROR

        key = selector.get_key(connection_socket)

        print('Preparing data to send ...')
        key.data.outb = UPDATE_VERSION_REQUEST
        print('Data ready to send.')
        response_event.clear()
        response_event.wait(timeout=None)
        if not response_event.is_set():
            print("Timeout waiting for client response.")
            return CONNECTION_SERVICE_ERROR
        
        update_version = response_data.get("update_version")

        dotenv.load_dotenv()
        database = os.getenv("SERVER_DATABASE")

        db_connection = sqlite3.connect(database)
        cursor = db_connection.cursor()
        # Gets the latest update file from the database
        update_version_stored = (cursor.execute("SELECT updates.update_version FROM vehicles JOIN updates ON vehicles.update_id = updates.update_id WHERE vehicles.vehicles_entry_id = ?;", (vehicle_entry_id,))).fetchone()
        cursor.execute("UPDATE vehicles SET last_poll_time = CURRENT_TIMESTAMP WHERE vehicles_entry_id = ?;", (vehicle_entry_id,))
        db_connection.commit()
        db_connection.close()

        if update_version_stored[0] == update_version:
            print("Client is up to date.")
        else:
            print("Client is not up to date.")
            print("Please update the client.")

        print(f"Client update version: {update_version}")
        
        response_data.clear()  # Clear the response data for the next request
        response_event.clear() # Clear the event for the next request
        print("Retrieved client update version successfully.")
        return SUCCESS
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return ERROR

def get_client_update_readiness_status(selector: selectors.SelectSelector, response_event: threading.Event, response_data: dict) -> typing.Tuple[bool, int]:
    try:
        _, client_host, client_port, ret_val = get_client_network_information()
        if ret_val == SUCCESS:
            print("Retreived client information.")
        else:
            print("An error occurred.")
            return ERROR
        
        selector, connection_socket, ret_val = create_connection(client_host, client_port, selector)
        if ret_val == SUCCESS:
            print("Connection to client established.")
        elif ret_val == CONNECTION_INITIATE_ERROR:
            print("Error: Connection initiation failed.")
            return CONNECTION_INITIATE_ERROR
        else:
            print("An error occurred.")
            return ERROR

        key = selector.get_key(connection_socket)

        print('Preparing data to send ...')
        key.data.outb = UPDATE_READINESS_STATUS_REQUEST
        print('Data ready to send.')

        response_event.clear()
        response_event.wait(timeout=None)
        if not response_event.is_set():
            print("Timeout waiting for client response.")
            return CONNECTION_SERVICE_ERROR
        
        update_readiness = response_data.get("update_readiness")
        print(update_readiness)
        print('hi')

        if update_readiness == True:
            print("Client is ready to receive the update.")

        if update_readiness == False:
            print("Client is not ready to receive the update.")
            return update_readiness, CLIENT_NOT_UPDATE_READY_ERROR
        
        response_data.clear()  # Clear the response data for the next request
        response_event.clear() # Clear the event for the next request
        print("Retrieved client update readiness successfully.")
        return update_readiness, SUCCESS
        

    except Exception as e:
        print(f"An error occurred: {e}")
        return BOOL_NONE, ERROR
    
def push_update(selector: selectors.SelectSelector, response_event: threading.Event, response_data: dict) -> int:
    try:
        _, client_host, client_port, ret_val = get_client_network_information()
        if ret_val == SUCCESS:
            print("Retreived client information.")
        else:
            print("An error occurred.")
            return ERROR

        selector, connection_socket, ret_val = create_connection(client_host, client_port, selector)
        if ret_val == SUCCESS:
            print("Connection to client established.")
        elif ret_val == CONNECTION_INITIATE_ERROR:
            print("Error: Connection initiation failed.")
            return CONNECTION_INITIATE_ERROR
        else:
            print("An error occurred.")
            return ERROR

        key = selector.get_key(connection_socket)

        print('Preparing data to send ...')
        key.data.file_name, file_data, _ = get_update_file() # Use socket for global file name access
        print(key.data.file_name)
        key.data.data_subtype = UPDATE_FILE
        key.data.outb = file_data
        print('Data ready to send.')

        response_event.clear()
        response_event.wait(timeout=None)
        if not response_event.is_set():
            print("Timeout waiting for client response.")
            return CONNECTION_SERVICE_ERROR
        
        if response_data.get("update_readiness") == False:
            print("Client is not ready to receive the update.")
            return CLIENT_NOT_UPDATE_READY_ERROR
        
        response_data.clear()  # Clear the response data for the next request
        response_event.clear() # Clear the event for the next request
        print("Pushed update successfully.")
        return SUCCESS
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return ERROR

# TODO: Needs to check latest update in database and compare with what is said the client has
def check_for_updates() -> typing.Tuple[bool, bytes, int]:
    update_available = True
    update_available_bytes = UPDATE_AVALIABLE
    return update_available, update_available_bytes, SUCCESS

# TODO: https://chatgpt.com/share/67e81027-c6bc-800e-adbc-2086ecf38797
# TODO: Use dedicated header file with more information
def get_update_file() -> typing.Tuple[bytes, bytes, int]:
    try:
        dotenv.load_dotenv()
        database = os.getenv("SERVER_DATABASE")

        print("Preparing update file ...")
        db_connection = sqlite3.connect(database)
        cursor = db_connection.cursor()
        # Gets the latest update file from the database
        update_version, update_file = (cursor.execute("SELECT update_version, update_file FROM updates ORDER BY update_id DESC LIMIT 1")).fetchone()
        db_connection.close()
        print(update_version)
        return str.encode(update_version), update_file, SUCCESS
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return STR_NONE, BYTES_NONE, ERROR