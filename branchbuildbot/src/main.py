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

BRANCH_CODENAME = "Pre Release"
BRANCH_VERSION = "0.6-pre"

import blog
import argparse
import os

from bsocket import connect
from handlecommand import handleCommand
from buildenvmanager import buildenv
from config import config

def main():
    print("Branch (BUILDBOT) - The AcaciaLinux package build system.")
    print("Copyright (c) zimsneexh 2022 (https://zsxh.eu/)")
    print("Version: "+ BRANCH_VERSION +" (" + BRANCH_CODENAME +")")
    print()

    # load config
    blog.info("Loading configuration file..")
    if(config.config.setup() != 0):
        return -1
 
    if(config.config.get_config_option("Logger")["EnableDebugLog"] == "True"):
        blog.enable_debug_level()
        blog.debug("Debug log enabled.")

    authkey = config.config.get_config_option("Connection")["AuthKey"]
    
    # replace authkey NONE with None
    if(authkey == "NONE"):
        authkey = None

    server_address = config.config.get_config_option("Connection")["ServerAddress"]
    server_port = int(config.config.get_config_option("Connection")["ServerPort"])
    identifier = config.config.get_config_option("Connection")["Identifier"]

    # init leafcore
    if(buildenv.init_leafcore() != 0):
        s = connect.connect(server_address, int(server_port), identifier, authkey, "BUILD")
        blog.info("Buildbot could not initialize leaf. Reporting system event.")
        connect.send_msg(s, "REPORT_SYS_EVENT {}".format("Buildbot setup failed because leaf is missing."))
        s.close()
        blog.info("Disconnected. Cannot continue.")
        return -1
   
    check_failed = False
    
    # check if the build environment is setup..
    blog.info("Checking build environments..")
    if(buildenv.check_buildenv() != 0):
        check_failed = True
  
    # establish socket connection
    s = connect.connect(server_address, int(server_port), identifier, authkey, "BUILD")

    if(s is None):
        blog.error("Connection refused.")
        return -1

    if(check_failed):
        blog.info("Buildbot setup failed, because leaf failed to deploy the build environment. Reporting system event.")
        connect.send_msg(s, "REPORT_SYS_EVENT {}".format("Buildbot setup failed because leaf failed to deploy the build environment."))
        s.close()
        blog.info("Disconnected. Cannot continue.")
        return -1

    if (not buildenv.check_host_binary("chroot")):
        blog.error("'chroot' binary is missing. Reporting system event.")
        connect.send_msg(s, "REPORT_SYS_EVENT {}".format("Buildbot setup failed because the 'chroot' binary is missing."))
        s.close()
        blog.info("Disconnected. Cannot continue")
        return -1

    if (not buildenv.check_host_binary("strip")):
        blog.error("'strip' binary is missing. Reporting system event.")
        connect.send_msg(s, "REPORT_SYS_EVENT {}".format("Buildbot setup failed because the 'strip' binary is missing."))
        s.close()
        blog.info("Disconnected. Cannot continue")
        return -1

    # Signal readyness to server
    blog.info("Sending ready signal...")
    res = connect.send_msg(s, "SIG_READY")

    if(res == "CMD_OK"):
        blog.info("Server acknowleged ready signal.")
    else:
        blog.error("Server did not acknowledge ready signal. Exiting.")
        return -1

    # always wait for cmds from masterserver
    while True:
        blog.info("Waiting for commands from masterserver...")
        cmd = connect.recv_only(s)
         
        # no data, server exited.
        if(cmd is None):
            blog.warn("Connection to server lost.")
            s.close()
            return -1

        blog.debug("Handling command from server.. {}".format(cmd))
        res = handleCommand.handle_command(s, cmd)

        if(res == None):
            blog.error("Critical failure. Disconnecting..")
            s.close()
            blog.info("Attempting recovery..")
            blog.info("Dropping build environment..")
            buildenv.drop_buildenv()
            blog.info("Recreating build environment..")
            buildenv.check_buildenv()
            blog.info("Reconnecting..")
            s = connect.connect(server_address, int(server_port), identifier, authkey, "BUILD")
        else:
            connect.send_msg(s, res)

if (__name__ == "__main__"):
    try:
        main()
    except KeyboardInterrupt:
        print()
        blog.info("Exiting on KeyboardInterrupt.")
        blog.info("Cleaning up..")
        buildenv.clean_env()
