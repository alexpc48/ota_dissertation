import selectors
import socket
import sys
import types

sel = selectors.DefaultSelector()


def accept_wrapper(sock):
    conn, addr = sock.accept()  # Should be ready to read
    print(f"Accepted connection from {addr}")
    conn.setblocking(False)
    data = types.SimpleNamespace(addr=addr, inb=b"", outb=b"")
    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    sel.register(conn, events, data=data)


def service_connection(key, mask):
    sock = key.fileobj
    data = key.data
    if mask & selectors.EVENT_READ:
        recv_data = sock.recv(1024)  # Should be ready to read
        if recv_data:
            data.outb += recv_data
        else:
            print(f"Closing connection to {data.addr}")
            sel.unregister(sock)
            sock.close()
    if mask & selectors.EVENT_WRITE:
        if data.outb:
            print(f"Echoing {data.outb!r} to {data.addr}")
            sent = sock.send(data.outb)  # Should be ready to write
            data.outb = data.outb[sent:]



# Checks usage of the script
if len(sys.argv) != 3:
    print(f"Usage: {sys.argv[0]} <host> <port>")
    sys.exit(1)

# Sets the host and port
host, port = sys.argv[1], int(sys.argv[2])

# Creates listening socket using IPv4 and TCP
lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# Binds the socket to the host and port
lsock.bind((host, port))
# Listens for connections
lsock.listen()
print(f"Listening on {(host, port)}")
# Sets the socket to non-blocking, preventing the server from locking up on operations
lsock.setblocking(False)
# Registers the socket to the selector to monitor for read events
sel.register(lsock, selectors.EVENT_READ, data=None)

try:
    while True:
        # The select gets the keys (what the object being monitored is)
        # and the mask (what the object is doing)
        # from the registered objects in the selector that are I/O ready
        # Single-threaded manner and handles sockets in the order that they are I/O ready
        # Select waits for any events on the registered sockets
        # The listening socket is registered which is how the selector can see new connections
        events = sel.select(timeout=None)
        # For the keys and masks within the
        for key, mask in events:
            if key.data is None:
                # Socket object is passed to the accept_wrapper function
                accept_wrapper(key.fileobj)
            else:
                # Handles non-new connections (connections already registered)
                service_connection(key, mask)
except KeyboardInterrupt:
    print("Caught keyboard interrupt, exiting")
finally:
    sel.close()