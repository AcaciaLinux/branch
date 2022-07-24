B_HOST = "127.0.0.1"
B_PORT = 27015
B_NAME = "debug-build"
B_TYPE = "BUILD"

from log import blog
from debugshell import debugshell
from package import package
from bsocket import connect
import argparse

def main():
    print("Branch (CLIENT) - The AcaciaLinux package build system.")
    print("Copyright (c) zimsneexh 2022 (https://zsxh.eu/)")
    print("Version: 0.1 (Point Insertion)")
    print()

    # TODO:
    # CONFIG FOR PORT

    s = connect.connect(B_NAME, B_TYPE)
    
    blog.info("Waiting for commands from masterserver..")
    # always wait for cmds from masterserver
    while True:
        cmd = s.recv(4000)
        


if (__name__ == "__main__"):
    try:
        main()
    except KeyboardInterrupt:
        print()
        blog.info("Exiting on KeyboardInterrupt.")
