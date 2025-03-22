# Libraries
import selectors, socket, sys, types

# Constants
SUCCESS = 0
ERROR = 1

# Variables
selector = selectors.DefaultSelector()

def accept_wrapper(socket):
    connection, address = socket.accept()
    print("Accepted connection from", address)
    connection.setblocking(False)
    data = types.SimpleNamespace(address=address, inb=b"", outb=b"")
    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    selector.register(connection, events, data=data)

def service_connection(key, mask):
    socket = key.fileobj
    data = key.data
    # If read operation
    if mask & selectors.EVENT_READ:
        recieved_data = socket.recv(1024)
        if recieved_data:
            data.outb += recieved_data
        else:
            print(f"Closing connection to {data.addr}")
            selector.unregister(socket)
            socket.close()
    # If write operation
    if mask & selectors.EVENT_WRITE:
        if data.outb:
            print(f"Echoing {data.outb!r} to {data.addr}")
            sent = socket.send(data.outb)
            data.outb = data.outb[sent:]

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <host> <port>")
        sys.exit(ERROR)
    host, port = sys.argv[1], int(sys.argv[2])
    listening_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listening_socket.bind((host, port))
    listening_socket.listen()
    print("Listening on", (host, port))
    listening_socket.setblocking(False)
    selector.register(listening_socket, selectors.EVENT_READ, data=None)
    try:
        while True:
            events = selector.select(timeout=None)
            for key, mask in events:
                if key.data is None:
                    accept_wrapper(key.fileobj)
                else:
                    service_connection(key, mask)
    except KeyboardInterrupt:
        print("Caught keyboard interrupt, exiting")
    except Exception as e:
        print(f"Caught exception: {e}")
    finally:
        selector.close()
        sys.exit(SUCCESS)