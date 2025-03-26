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

    messages = [b"Message 1 from client.", b"Message 2 from client."]
    # Initiate a connection to the server
    connection_socket, ret_val = initiate_connection(server_host, server_port, messages, selector)
    # if ret_val != SUCCESS:
    #     print('Failed to initiate connection')
    #     time.sleep(2) # Debugging purposes
    #     continue
    try:
        while True:


            time.sleep(2) # Debugging purposes

            events = selector.select(timeout=1)
            if events:
                for key, mask in events:
                    # Service events
                    if mask & selectors.EVENT_READ:
                        recv_data = connection_socket.recv(1024)  # Should be ready to read
                        if recv_data:
                            print(f"Received {recv_data!r} from connection")
                            key.data.recv_total += len(recv_data)
                        if not recv_data or key.data.recv_total == key.data.msg_total:
                            close_connection(connection_socket, selector)
                    if mask & selectors.EVENT_WRITE:
                        if not key.data.outb and key.data.messages:
                            key.data.outb = key.data.messages.pop(0)
                        if key.data.outb:
                            print(f"Sending {key.data.outb!r} to connection")
                            sent = connection_socket.send(key.data.outb)  # Should be ready to write
                            key.data.outb = key.data.outb[sent:]
                
            # _ = close_connection(connection_socket, selector)

            time.sleep(2) # Debugging purposes

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        selector.close()
        print("Connection closed.")
        sys.exit(ret_val)