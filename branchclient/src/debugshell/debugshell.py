import socket
from bsocket import connect

def run_shell():
    s = connect.connect("debug-shell", "CONTROLLER")

    while True:
        print("[branch] ~> ", end = '')
        line = input()
        
        if(line is ""):
            continue

        s.sendall(bytes(line, "utf-8"))
        data = s.recv(4096)
        print("Response: " + data.decode("utf-8"))


