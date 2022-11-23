# Branch - The AcaciaLinux package build system
# Copyright (c) 2021-2022 zimsneexh (https://zsxh.eu/)

# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

BRANCH_CODENAME = "Water Hazard"
BRANCH_VERSION = "0.4"

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
    print("Version: "+ BRANCH_VERSION +" (" + BRANCH_CODENAME +")")
    print()

    # load config
    blog.info("Loading configuration file..")
    conf = config.branch_options()
     
    # init leafcore
    blog.debug("About to initialize leafcore..")
    if(buildenv.init_leafcore() != 0):
        return -1
   
    # check if the build environment is setup..
    blog.info("Checking build environments..")
    if(buildenv.check_buildenv() != 0):
        return -1
 
    # establish socket connection
    s = connect.connect(conf.serveraddr, conf.serverport, conf.identifier, conf.authkey, B_TYPE)

    if(s is None):
        blog.error("Connection refused.")
        exit(-1)

    # Signal readyness to server
    blog.info("Sending ready signal...")
    res = connect.send_msg(s, "SIG_READY")

    if(res == "CMD_OK"):
        blog.info("Server acknowleged ready signal.")
    else:
        blog.debug("Did not receive ready signal. Exiting..")
        return -1

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
