# Libraries
import sys
from server_functions import *
from server_thread_functions import *

# dotenv.load_dotenv(override=True)

# Main program
if __name__=='__main__':
    try:
        tracemalloc.stop()
    except:
        pass
    tracemalloc.start()
    # Create a selector object
    selector = selectors.SelectSelector()

    dotenv.load_dotenv()
    database = os.getenv("SERVER_DATABASE")
    # Get local host and port for the listening socket
    db_connection = sqlite3.connect(database)
    cursor = db_connection.cursor()
    result = (cursor.execute("SELECT local_ip, local_port FROM network_information WHERE network_id = 1")).fetchone()
    db_connection.close()
    local_host, local_port = result[0], result[1]
    
    # Create listening socket so that the client can connect
    #print(f"Creating listening socket on {local_host}:{local_port} ...")
    ret_val = create_listening_socket(local_host, local_port, selector)
    if ret_val != SUCCESS:
        #print('Failed to create listening socket')
        sys.exit(ret_val)

    response_event = threading.Event() # Used to signal when a connection has been serviced
    response_data = {} # Data dictionary for global access

    # Start threads
    # Shows the options menu
    options_menu_thread = threading.Thread(target=menu_thread, daemon=False, args=(selector, response_event, response_data))

    # Constantly listens for new connections
    listen_thread = threading.Thread(target=listen, daemon=False, args=(selector,))

    # Services any active connections
    service_connection_thread = threading.Thread(target=service_connection, daemon=False, args=(selector, response_event, response_data))

    # Start the threads
    options_menu_thread.start()
    listen_thread.start()
    service_connection_thread.start()

    # TODO: Implement proper exit handling for threads (daemon, os._exit(), thread.join(), etc.)
    # If the threads fail, the program should stop/exit