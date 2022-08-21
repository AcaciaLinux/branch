import socket
from bsocket import connect

def run_shell(conf):
    s = connect.connect(conf.serveraddr, conf.serverport, "debug-shell", "CONTROLLER")

    while True:
        print("[branch] ~> ", end = '')
        line = input()
        
        if(line is ""):
            continue

        connect.send_msg(s, line)
        data = connect.recv_only(s)
        print("Response: {}".format(data))


