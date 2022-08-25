BRANCH_CODENAME = "A Red Letter Day"
BRANCH_VERSION = "0.2"

B_TYPE = "BUILD"

from log import blog
from package import build
from bsocket import connect
from handlecommand import handleCommand
from buildenvmanager import buildenv
from config import config

import argparse
import os

def main():
    print("Branch (BUILDBOT) - The AcaciaLinux package build system.")
    print("Copyright (c) zimsneexh 2022 (https://zsxh.eu/)")
    print("Version: 0.1 (Point Insertion)")
    print()

    # load config
    blog.info("Loading configuration file..")
    conf = config.load_config()

    buildenv.check_buildenv()

    # establish socket connection
    s = connect.connect(conf.serveraddr, conf.serverport, conf.identifier, B_TYPE)

    if(s is None):
        blog.error("Connection refused.")
        exit(-1)

    # Signal readyness to server
    blog.info("Sending ready signal...")
    res = connect.send_msg(s, "SIG_READY")

    if(res == "CMD_OK"):
        blog.info("Server acknowleged ready signal.")
    else:
        return

    blog.info("Waiting for commands from masterserver...")
    # always wait for cmds from masterserver
    while True:
        cmd = connect.recv_only(s)
        
        # no data, server exited.
        if(cmd is None):
            blog.warn("Connection to server lost.")
            s.close()
            exit(0)

        blog.debug("Handling command from server.. {}".format(cmd))
        res = handleCommand.handle_command(s, cmd) 
        connect.send_msg(s, res) 

if (__name__ == "__main__"):
    try:
        main()
    except KeyboardInterrupt:
        print()
        blog.info("Exiting on KeyboardInterrupt.")
        blog.info("Cleaning up..")
        buildenv.clean_env()
