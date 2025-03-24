# Libraries
import sys
import selectors
import time

from connections import *

# Main program
if __name__=='__main__':
    # Create a selector object
    selector = selectors.DefaultSelector()
    
    # Assign the server IP address and port
    server_host, server_port = sys.argv[1], int(sys.argv[2])
    
    try:
        while True:
            # Initiate a connection to the server
            connection_socket, _ = initiate_connection(server_host, server_port, selector)
            
            time.sleep(5)

            _ = close_connection(connection_socket, selector)

            time.sleep(5)
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        selector.close()
        connection_socket.close()
        print("Connection closed.")