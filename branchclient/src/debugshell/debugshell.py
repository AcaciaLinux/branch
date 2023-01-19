import socket
import blog

from bsocket import connect

#
# Connect to server and run debug shell
#
def run_shell(s):
    if(s is None):
        blog.error("Connection refused.")
        exit(-1)

    while True:
        print("[branch] ~> ", end = '')
        line = ""
        
        try:
            line = input()
        except Exception:
            return

        if(line == ""):
            continue

        data = connect.send_msg(s, line)
        print("Response: {}".format(data))


