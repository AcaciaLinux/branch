import socket
import main
import blog

#
# connect to server, send type, authkey and name..
#
def connect(host, port, name, authkey, cltype):
    blog.info("Connecting to server...")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((host, port))
    except ConnectionRefusedError:
        blog.error("Connection refused.")
        return None

    blog.info("Connection established!")
   
    if(authkey is not None):
        blog.info("Sending auth key..")
            
        cmd = "AUTH " + authkey
        data = send_msg(s, cmd)
        
        if(data == "AUTH_OK"):
            blog.info("Authkey accepted.")
        else:
            blog.error("An error occured: {}".format(data))
            return None

    blog.info("Sending machine type..")
    cmd = "SET_MACHINE_TYPE {}".format(cltype)

    data = send_msg(s, cmd)
    
    if(data == "CMD_OK"):
        blog.info("Machine type granted.")
    else:
        blog.error("An error occured: {}".format(data))
        return None

    blog.info("Sending client name...")
    cmd = "SET_MACHINE_NAME {}".format(name)
    
    data = send_msg(s, cmd)
    
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

    data_trimmed = data[data_str_loc+1:len(data)]
    
    if(data_str_loc == -1):
        blog.error("Connection failed.")
        return None

    try:
        cmd_bytes = int(data_str[0:data_str_loc])
    except ValueError:
        blog.warn("Byte count error from Server.")
        return None

    while(len(data_trimmed) != cmd_bytes):
        data_trimmed += socket.recv(4096)

    return data_trimmed.decode("utf-8")

#
# send msg to server and read response
#
def send_msg(socket, cmd):
    cmd = "{} {}".format(len(bytes(cmd, "utf-8")), cmd)
    socket.sendall(bytes(cmd, "utf-8"))
    data = recv_only(socket)
    return data

