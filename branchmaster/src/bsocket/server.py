import selectors
import socket

from log import blog
from manager import client

# Initialize DefaultSelector
sel = selectors.DefaultSelector()

def init_server(addr, port):
    # sock opts
    sock = socket.socket()
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind((addr, port))
    except Exception as ex:
        blog.error("Branchmaster failed to initialize: {}".format(ex))
        blog.error("Thread exiting.")
        return

    sock.listen(100)
    sock.setblocking(False)

    # register EVENT_READ to accept() func
    sel.register(sock, selectors.EVENT_READ, accept)
    
    # main event loop
    while True:
        events = sel.select()
        for key, mask in events:
            callback = key.data
            callback(key.fileobj, mask)

def accept(sock, mask):
    # Accept the socket connection
    conn, addr = sock.accept()
    blog.info("Accepted client connection from {}".format(conn.getpeername()))

    # create a new client object
    cl = client.Client(conn, sel)

    # reregister EVENT_READ to actual read function
    sel.register(conn, selectors.EVENT_READ, cl.receive_command)
