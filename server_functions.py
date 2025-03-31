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
    print("10. Get the client update readiness status") # TODO
    print("11. Get the client update status") # TODO: Check if the update has been installed, failed, behind, etc.
    print("12. Get the client update version") # TODO
    print("-------------------------------------------------------------------------------------------")
    print("20. Change the update file") # TODO
    print("-------------------------------------------------------------------------------------------")
    print("98. Redisplay the options menu")
    print("99. Exit")
    print("-------------------------------------------------------------------------------------------")

    return input("Enter an option: ")

def push_update(selector: selectors.SelectSelector, response_event: threading.Event, response_data: dict) -> int:
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
        
        vehicle_id_input = int(input("Enter the vehicle ID to push the update to: "))

        # AI help for next() function
        selected_vehicle = next((v for v in query_result if v[0] == vehicle_id_input), None)

        client_host = selected_vehicle[2]
        client_port = selected_vehicle[3]

        selector, connection_socket, ret_val = create_connection(client_host, client_port, selector)
        if ret_val == SUCCESS:
            print("Connection to client established.")
        elif ret_val == CONNECTION_INITIATE_ERROR:
            print("Error: Connection initiation failed.")
            return CONNECTION_INITIATE_ERROR
        else:
            print("An error occurred while establishing the connection.")
            return ERROR

        key = selector.get_key(connection_socket)

        print('Preparing data to send ...')
        key.data.outb = UPDATE_READINESS_REQUEST
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
def get_update_file() -> typing.Tuple[bytes, int]:
    try:
        dotenv.load_dotenv()
        database = os.getenv("SERVER_DATABASE")

        print("Preparing update file ...")
        db_connection = sqlite3.connect(database)
        cursor = db_connection.cursor()
        # Gets the latest update file from the database
        update_version, update_file = (cursor.execute("SELECT update_version, update_file FROM updates ORDER BY update_id DESC LIMIT 1")).fetchone()
        db_connection.close()

        file_data = str.encode(update_version) + FILE_HEADER_SECTION_END + update_file + EOF_TAG_BYTE + RECEIVED_FILE_CHECK_REQUEST
        return file_data, SUCCESS
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return b'', ERROR