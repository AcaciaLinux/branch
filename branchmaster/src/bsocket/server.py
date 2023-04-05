import selectors
import socket
import blog

from manager import client
from _thread import *
import os

# Initialize DefaultSelector
sel = selectors.DefaultSelector()
STAGING_AREA = "staging"

def init_server(addr, port):
    blog.debug("Socket server initializing.")

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # tcp keepalive
    s.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 5)
    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)
    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 5)

    blog.debug("Binding socket server to {} port {}".format(addr, port))
    s.bind((addr, port))
    
    blog.debug("Setting listening type to 5")
    s.listen(5)

    blog.debug("Checking staging area")
    if(not os.path.exists(STAGING_AREA)):
        os.mkdir(STAGING_AREA)

    blog.debug("Listening for clients..")
    while True:
        c, addr = s.accept()
        blog.debug("Client connection established. Spawning thread")
        start_new_thread(threaded_client_handler, (c,))
        blog.debug("Connection handled. Listening..")


def threaded_client_handler(client_socket):
    blog.debug("Starting thread client handler.")
    
    _client = client.Client(client_socket)
    blog.info("New client initialized. UUID: {}".format(_client.get_identifier()))

    while True:
        if(_client.file_transfer_mode):
            _client.receive_file()
        else:
            blog.debug("Receiving initial message from client..")
            data = None
            try:
                data = receive_data(_client)
            except ConnectionResetError:
                blog.warn("Connection to client reset. Handling disconnect..")
                _client.handle_disconnect()
            except TimeoutError:
                blog.warn("Connection to client timed out. Handling disconnect..")
                _client.handle_disconnect()

            if(data is None or data == b""):
                _client.handle_disconnect()
                break
            
            data_str = ""

            try:
                data_str = data.decode("utf-8")
            except UnicodeDecodeError:
                _client.handle_disconnect()
                break
            
            cmd_bytes = 0
            data_trimmed = data[data_str.find(" ") + 1:len(data)]
            
            try:
                cmd_bytes = int(data_str[0:data_str.find(" ")])
            except ValueError:
                _client.handle_disconnect()
                break

            blog.debug("Full message is {} bytes.".format(cmd_bytes))

            while(len(data_trimmed) != cmd_bytes):
                data_trimmed += receive_data(_client)
        
            blog.debug("Received {} bytes from client.".format(cmd_bytes))
           
            data_trimmed_str = data_trimmed.decode("utf-8")

            if(data_trimmed):
                manager_res = _client.receive_command(data_trimmed_str)

                if(manager_res is not None):
                    blog.debug("Sending message to client {}: {}".format(_client.get_identifier(), manager_res))
                    
                    _client.lock.acquire()
                    try:
                        client_socket.sendall("{} {}".format(len(manager_res), manager_res).encode("utf-8"))
                        _client.lock.release()
                    except BrokenPipeError:
                        _client.lock.release()
                        _client.handle_disconnect()


            else:
                blog.debug("Client disconnected.")
                _client.handle_disconnect()
    
    blog.debug("Client thread exiting.")

def receive_data(client):
    try:
        return client.socket.recv(4096)
    except ConnectionResetError:
        return None
