import selectors
import socket

from log import blog
from manager import client
from manager import manager
from _thread import *
import threading
import os
import shutil

# Initialize DefaultSelector
sel = selectors.DefaultSelector()
STAGING_AREA = "staging"

def init_server(addr, port):
    blog.info("Socket server initializing.")

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    blog.debug("Binding socket server to {} port {}".format(addr, port))
    s.bind((addr, port))
    
    blog.debug("Setting listening type to 5")
    s.listen(5)

    blog.debug("Checking pkg-staging area")
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

    _client.client_thread = threading.current_thread()

    while True:
        if(_client.file_transfer_mode):
            receive_file(client_socket, _client)
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
            data_trimmed = data_str[data_str.find(" ") + 1:len(data_str)]
            
            try:
                cmd_bytes = int(data_str[0:data_str.find(" ")])
            except ValueError:
                _client.handle_disconnect()
                break

            blog.debug("Full message is {} bytes.".format(cmd_bytes))

            while(len(data_trimmed) != cmd_bytes):
                data_trimmed += receive_data(_client).decode("utf-8")
        
            blog.debug("Received full message from client.")
            
            if(data_trimmed):
                blog.debug("Command from {}: {}".format(_client.get_identifier(), data_trimmed))
                manager_res = _client.receive_command(data_trimmed)
                if(manager_res is not None):
                    blog.debug("Sending message to client {}: {}".format(_client.get_identifier(), manager_res))
                    client_socket.sendall("{} {}".format(len(manager_res), manager_res).encode("utf-8"))
                else:
                    blog.debug("Got empty response from manager. Ignoring")

            else:
                blog.debug("Client disconnected.")
                _client.handle_disconnect()
    
    manager.manager().report_system_event("Branchmaster", "Client {} disconnected.".format(_client.get_identifier()))
    blog.debug("Client thread exiting.")

#
# Receive a file from buildbot
#
def receive_file(socket, client):
    job = manager.manager().get_job_by_client(client)
    
    if(job is None):
        blog.error("Buildbot attempted to submit file while not having a job assigned?")
        return

    out_file = open(job.file_name, "wb")
    data_len = 0

    blog.info("File transfer started from {}. Receiving {} bytes from buildbot..".format(client.get_identifier(), job.file_size))
    
    while(job.file_size != data_len):
        data = socket.recv(4096)
        if(data == b""):
            break

        data_len += len(data)
        out_file.write(data)

    if(data_len == job.file_size):
        blog.info("Received {} bytes. File upload successful".format(job.file_size))
        out_file.close()

        client.file_transfer_mode = False
        client.send_command("UPLOAD_ACK")
        blog.info("File upload completed.")
    else:
        blog.warn("File upload failed, because the client disconnected.")
        client.file_transfer_mode = False

def receive_data(client):
    try:
        return client.sock.recv(4096)
    except ConnectionResetError:
        return None
