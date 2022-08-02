import socket
import main
from log import blog


def connect(name, cltype):
    host = main.B_HOST
    port = main.B_PORT

    blog.info("Connecting to server..")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))

    blog.info("Connection established.")
    
    blog.info("Sending machine type..")
    cmd = "SET_MACHINE_TYPE " + cltype
    s.sendall(bytes(cmd, "utf-8"))
    data = s.recv(4096)
    if(data.decode("utf-8") == "CMD_OK"):
        blog.info("Machine type granted.")
    else:
        blog.error("An error occured: {}".format(data))
        return None

    blog.info("Sending client name...")
    
    cmd = "SET_MACHINE_NAME " + name
    s.sendall(bytes(cmd, "utf-8"))
    data = s.recv(4096)
    
    if(data.decode("utf-8") == "CMD_OK"):
        blog.info("Client name accepted.")
    else:
        blog.error("An error occured: {}".format(data))
        return None

    return s


def send_msg(socket, cmd):
    socket.sendall(bytes(cmd, "utf-8"))
    data = socket.recv(4096)
    return data.decode("utf-8")

