# Libraries
import selectors
import sys
import time

from functions import *
from constants import *

# Main program
if __name__=='__main__':
    # Create a selector object
    selector = selectors.DefaultSelector()
    
    # Assign the server IP address and port number
    server_host, server_port = sys.argv[1], int(sys.argv[2])
    
    # Create a listening socket to accept new connections
    ret_val = create_listening_socket(server_host, server_port, selector)
    if ret_val != SUCCESS:
        print('Failed to create listening socket')
        sys.exit(ret_val)

    # Main loop
    try:
        # Run the server indefinitely
        while True:
            # Get list of events from the selector
            events = selector.select(timeout=None) # Timeout controls how long to wait for an event before exiting (none so server is always listening)
            
            # Logic to service each event
            for key, mask in events:
                # TODO: Check if event is from authenticated source and use something more secure than IP address to authenticate
                
                # If the event comes from the listening socket, accept a new connection
                if key.data == "listening_socket":
                    ret_val = accept_new_connection(key.fileobj, selector)
                    if ret_val != SUCCESS:
                        print('Failed to accept new connection')
                        continue

                # Otherwise, service the current connection
                else:
                    ret_val = service_current_connection(key, mask, selector, b'hello there EOF')
                    if ret_val == SUCCESS:
                        time.sleep(2) # Debugging purposes
                        sys.exit(ret_val)

    except Exception as e:
        print(f"An error occurred: {e}")

    except KeyboardInterrupt:
        print("Keyboard interrupt received.")
        ret_val = KEYBOARD_INTERRUPT

    # Final excecution
    finally:
        selector.close()
        print("Server closed.")
        sys.exit(ret_val)