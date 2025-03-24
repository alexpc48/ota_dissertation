

import selectors
import socket
import sys
import types

sel = selectors.DefaultSelector()

from datetime import datetime

# Get the current time
#datetime.now() = datetime.now()

# Format the time to include hours, minutes, seconds, and milliseconds
#datetime.now() = datetime.now().strftime("%H:%M:%S") + f".{datetime.now().microsecond // 1000:03d}"

import time
def accept_wrapper(sock):
    time.sleep(1)
    conn, addr = sock.accept()  # Should be ready to read
    print(f"{datetime.now()} Accepted {conn} from {addr}")
    conn.setblocking(False)
    data = types.SimpleNamespace(addr=addr, inb=b"", outb=b"")
    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    sel.register(conn, events, data=data)


def service_connection(key, mask):
    time.sleep(1)
    sock = key.fileobj
    data = key.data
    if mask & selectors.EVENT_READ:
        recv_data = sock.recv(1024)  # Should be ready to read
        if recv_data:
            print(f"{datetime.now()} Received {recv_data!r} from {data.addr}")
            data.outb += recv_data
        else:
            print(f"{datetime.now()} Closing connection to {data.addr}")
            sel.unregister(sock)
            sock.close()
    if mask & selectors.EVENT_WRITE:
        time.sleep(1)
        if data.outb:
            print(f"{datetime.now()} Echoing {data.outb!r} to {data.addr}")
            sent = sock.send(data.outb)  # Should be ready to write
            data.outb = data.outb[sent:]


if len(sys.argv) != 3:
    print(f"Usage: {sys.argv[0]} <host> <port>")
    sys.exit(1)

host, port = sys.argv[1], int(sys.argv[2])
lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
lsock.bind((host, port))
lsock.listen()
print(f"{datetime.now()} Listening on {(host, port)}")
lsock.setblocking(False)
sel.register(lsock, selectors.EVENT_READ, data="listening_socket")

try:
    while True:
        events = sel.select(timeout=None)
        for key, mask in events:
            if key.data == "listening_socket":
                accept_wrapper(key.fileobj)
            else:
                service_connection(key, mask)
except KeyboardInterrupt:
    print("Caught keyboard interrupt, exiting")
finally:
    sel.close()