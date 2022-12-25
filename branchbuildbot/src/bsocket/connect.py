import socket
import main
import os
import time

from log import blog

#
# connect to server, send type, authkey and name..
#
def connect(host, port, name, authkey, cltype):
    blog.info("Connecting to server...")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    s.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 1)
    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 3)
    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 5)

    try:
        s.connect((host, port))
    except ConnectionRefusedError:
        blog.error("Connection refused.")
        exit(-1)

    blog.info("Connection established!")
   
    if(authkey is not None):
        blog.info("Sending auth key..")
            
        cmd = "AUTH " + authkey
        cmd = "{} {}".format(len(cmd), cmd)

        s.sendall(bytes(cmd, "utf-8"))
        
        data = recv_only(s)
        
        if(data == "AUTH_OK"):
            blog.info("Authkey accepted.")
        else:
            blog.error("An error occured: {}".format(data))
            return None

    blog.info("Sending machine type..")
    cmd = "SET_MACHINE_TYPE " + cltype
    cmd = "{} {}".format(len(cmd), cmd)

    s.sendall(bytes(cmd, "utf-8"))
    data = recv_only(s)
    
    if(data == "CMD_OK"):
        blog.info("Machine type granted.")
    else:
        blog.error("An error occured: {}".format(data))
        return None

    blog.info("Sending client name...")
    cmd = "SET_MACHINE_NAME " + name
    cmd = "{} {}".format(len(cmd), cmd)
    
    s.sendall(bytes(cmd, "utf-8"))
    data = recv_only(s)
    
    if(data == "CMD_OK"):
        blog.info("Client name accepted.")
    else:
        blog.error("An error occured: {}".format(data))
        return None

    return s

#
# recv data from socket, read BYTES
#
def recv_only(socket):
    data = None

    try:
        data = socket.recv(4096)
    except ConnectionResetError:
        return None

    data_str = data.decode("utf-8")
    data_str_loc = data_str.find(" ")
    cmd_bytes = 0

    data_trimmed = data_str[data_str_loc+1:len(data_str)]

    if(data_str_loc == -1):
        blog.info("Connection failed.")
        return None

    try:
        cmd_bytes = int(data_str[0:data_str_loc])
    except ValueError:
        blog.warn("Byte count error from Server.")
        return None

    while(len(data_trimmed) != cmd_bytes):
        data_trimmed += socket.recv(4096).decode("utf-8")

    return data_trimmed

def send_only(socket, cmd):
    cmd = "{} {}".format(len(bytes(cmd, "utf-8")), cmd)
    socket.sendall(bytes(cmd, "utf-8"))

#
# send msg to server and read response
#
def send_msg(socket, cmd):
    cmd = "{} {}".format(len(bytes(cmd, "utf-8")), cmd)
    socket.sendall(bytes(cmd, "utf-8"))
    data = recv_only(socket)
    return data

#
# sends a file to the server using socket sendfile function
#
def send_file(socket, filename):
    file = open(filename, "rb")

    file_size = os.path.getsize(filename)
    bytes_sent = 0
    start_time = time.time()
    elapsed_time = 0

    while True:
        # Use sendfile to transfer the contents of the file
        # directly to the network buffer
        bytes_sent += socket.sendfile(file, bytes_sent, file_size - bytes_sent)

        # Print progress report every 10 seconds
        elapsed_time += time.time() - start_time
        start_time = time.time()
        if(elapsed_time > 10):
            speed = bytes_sent / elapsed_time / 1024
            blog.info("{:.2f} KB / {:.2f} KB, {:.2f} KB/sec".format(bytes_sent / 1024, file_size / 1024, speed))
            elapsed_time = 0  # Reset elapsed time

        # we are done sending
        if(bytes_sent == file_size):
            break
    
    res = recv_only(socket)
    return res
