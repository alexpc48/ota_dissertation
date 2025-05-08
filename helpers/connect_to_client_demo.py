# File used as part of demo for force connecting to an insecure client
# Demo straight for the Windows client

import socket
import selectors
import time
import types
import errno

def connect_to_windows_client() -> int:
    try:
        host, port = '192.168.225.150', 50150
        selector = selectors.SelectSelector()
        connection_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connection_socket.setblocking(False)
        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        data = types.SimpleNamespace(address=(host, port), inb=None, outb=None, connected=False)
        
        # Waits for the connection to complete in a non-blocking way, but blocks all other operations
        connection_attempts = 0
        while not data.connected:
            err = connection_socket.connect_ex((host, port)) # Try connecting
            if err == 10056 or err == 1: # Connection made
                print(f"Connection to {host}:{port} successful.")
                data.connected = True
                break
            elif err == 10035 or err == errno.EINPROGRESS or err == errno.EALREADY: # Non-blocking connection in progress
                #print(f"Connection to {host}:{port} in progress ...")
                time.sleep(1)
                continue
            elif err == 10022 or err == errno.EINVAL: # Failed connction (no client at the address)
                #print("No device found at the specified address.")
                # Try up to 5 times to connect to the client
                if connection_attempts > 5:
                    #print("Connection attempts exceeded. Exiting ...")
                    return 0
                #print("Trying again ...")
                time.sleep(5)
                connection_attempts += 1
                continue
            else:
                print(f"Connection to {host}:{port} failed with error: {errno.errorcode[err]}\n")
                print("Please check the host and port details.")
                return 0


        # Register the connection with the selector for read and write events
        selector.register(connection_socket, events, data=data)
        print("Socket registered.")

        return 1
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return 0
    

if __name__ == "__main__":
    connect_to_windows_client()