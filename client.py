# Libraries
import sys
import selectors
import time

from functions import *
from constants import *

# Main program
if __name__=='__main__':
    # Create a selector object
    selector = selectors.DefaultSelector()
    
    # Assign the server IP address and port
    server_host, server_port = sys.argv[1], int(sys.argv[2])

    # Initiate a connection to the server
    connection_socket, ret_val = initiate_connection(server_host, server_port, selector)
    if ret_val != SUCCESS:
        print('Failed to initiate connection')
        time.sleep(2) # Debugging purposes
        sys.exit(ret_val)

    time.sleep(2) # Debugging purposes

    try:
        while True:
            events = selector.select(timeout=1)
            if events:
                for key, mask in events:
                    ret_val = service_current_connection(key, mask, selector, None)
                    if ret_val == SUCCESS:
                        time.sleep(2) # Debugging purposes
                        sys.exit(ret_val)
                
            # _ = close_connection(connection_socket, selector)

            time.sleep(2) # Debugging purposes

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        selector.close()
        print("Connection closed.")
        sys.exit(ret_val)