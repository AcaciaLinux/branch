import socket

from bsocket import connect
from log import blog

#
# Connect to server and run debug shell
#
def run_shell(s):

    if(s is None):
        blog.error("Connection refused.")
        exit(-1)

    while True:
        print("[branch] ~> ", end = '')
        line = input()
        
        if(line == ""):
            continue

        data = connect.send_msg(s, line)
        print("Response: {}".format(data))


