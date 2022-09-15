import socket
import main

from log import blog

#
# connect to server, send type and name..
#
def connect(host, port, name, cltype):
    blog.info("Connecting to server...")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((host, port))
    except ConnectionRefusedError:
        return None

    blog.info("Connection established!")
    
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
        data = socket.recv(8192)
    except ConnectionResetError:
        return None

    data_str = data.decode("utf-8")
    data_str_loc = data_str.find(" ")
    cmd_bytes = 0

    data_trimmed = data_str[data_str_loc+1:len(data_str)]
    
    try:
        cmd_bytes = int(data_str[0:data_str_loc])
    except ValueError:
        blog.warn("Byte count error from Server.")
        return None

    while(len(data_trimmed) != cmd_bytes):
        data_trimmed += socket.recv(8192).decode("utf-8")

    return data_trimmed

#
# send msg to server and read response
#
def send_msg(socket, cmd):
    cmd = "{} {}".format(len(bytes(cmd, "utf-8")), cmd)
    socket.sendall(bytes(cmd, "utf-8"))
    data = recv_only(socket)
    return data

