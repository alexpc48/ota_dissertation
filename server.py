# Libraries
import selectors
import sys

from socket_creation_wrapper import *
from connections import *

# Main program
if __name__=='__main__':
    # Create a selector object
    selector = selectors.DefaultSelector()
    
    # Assign the server IP address and port
    server_host, server_port = sys.argv[1], int(sys.argv[2])
    
    # Create listening socket
    _ = create_listening_socket(server_host, server_port, selector)

    # Main loop
    try:
        while True:
            # Get list of events from the selector
            events = selector.select(timeout=None) # Timeout controls how long to wait for an event before returning
            
            for key, mask in events:
                # If the event comes from the listening socket, accept a new connection
                if key.data == "listening_socket":
                    accept_new_connection(key.fileobj, selector)
                # Otherwise, service the current connection
                else:
                    service_current_connection(key, mask, selector)

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Close connections used
        selector.close()
        # listening_socket.close()
        print("Server closed.")