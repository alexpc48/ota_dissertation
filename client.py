# Libraries
import sys
import selectors
import time

from connections_wrapper import *
from constants import *

# Main program
if __name__=='__main__':
    # Create a selector object
    selector = selectors.DefaultSelector()
    
    # Assign the server IP address and port
    server_host, server_port = sys.argv[1], int(sys.argv[2])
    
    try:
        while True:
            # Initiate a connection to the server
            connection_socket, ret_val = initiate_connection(server_host, server_port, selector)
            if ret_val != SUCCESS:
                print('Failed to initiate connection')
                time.sleep(2) # Debugging purposes
                continue

            time.sleep(2) # Debugging purposes
            events = selector.select(timeout=1)
            if events:
                for key, mask in events:
                    print(type(key))
                    print(type(mask))
                    print(mask)
                    service_connection(key, mask)
                connection_socket.sendall(b"Hello, server!")
            print("Data sent to server.")
            
            time.sleep(2) # Debugging purposes

            _ = close_connection(connection_socket, selector)

            time.sleep(2) # Debugging purposes

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        selector.close()
        print("Connection closed.")
        sys.exit(ret_val)