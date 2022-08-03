BRANCH_CODENAME="Point Insertion"
BRANCH_VERSION="0.1"

B_HOST = "127.0.0.1"
B_PORT = 27015
B_NAME = "debug-build"
B_TYPE = "BUILD"

from log import blog
from package import package
from bsocket import connect
from handlecommand import handleCommand
import argparse

def main():
    print("Branch (BUILDBOT) - The AcaciaLinux package build system.")
    print("Copyright (c) zimsneexh 2022 (https://zsxh.eu/)")
    print("Version: 0.1 (Point Insertion)")
    print()

    # TODO:
    # CONFIG FOR PORT

    s = connect.connect(B_NAME, B_TYPE)

    # Signal readyness to server
    blog.info("Sending ready signal")
    res = connect.send_msg(s, "SIG_READY")

    if(res == "CMD_OK"):
        blog.info("Server accepted ready status..")
    else:
        return

    blog.info("Waiting for commands from masterserver..")
    # always wait for cmds from masterserver
    while True:
        cmd = connect.recv_only(s)
        
        # no data, server exited.
        if(cmd is ""):
            blog.warn("Connection to server lost. Exiting.")
            s.close()
            exit(0)

        blog.debug("Handling command from server.. {}".format(cmd))
        res = handleCommand.handle_command(cmd) 
        connect.send_msg(s, res) 

if (__name__ == "__main__"):
    try:
        main()
    except KeyboardInterrupt:
        print()
        blog.info("Exiting on KeyboardInterrupt.")
