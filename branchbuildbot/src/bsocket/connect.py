import socket
import main
import os

from log import blog

#
# connect to server, send type, authkey and name..
#
def connect(host, port, name, authkey, cltype):
    blog.info("Connecting to server...")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    s.setsocketopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    s.setsocketopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 1)
    s.setsocketopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 3)
    s.setsocketopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 5)

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
# send file
#
def send_file(socket, filename):
    file = open(filename, "rb")

    blog.info("Uploading file to masterserver...")

    bytes_sent = 0
    file_size = os.path.getsize(filename)

    while True:
        print("{} bytes / {} bytes".format(bytes_sent, file_size))
        bytes_read = file.read(4096)
        bytes_sent += len(bytes_read)

        # we are done reading
        if(not bytes_read):
            break

        socket.sendall(bytes_read)
   
    print()
    res = recv_only(socket)
    return res

