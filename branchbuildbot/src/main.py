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
import os
import json
import traceback
import branchclient

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

    # establish socket connection
    bc = branchclient.branchclient(server_address, int(server_port), identifier, authkey, "BUILD")

    if(not bc.ready):
        return -1

    # provide system performance metrics
    blog.info("Providing system information..")
    bc.send_recv_msg("SET_MACHINE_INFORMATION {}".format(json.dumps(buildenv.get_host_info())))

      
    deployment_config = json.loads(bc.send_recv_msg("GET_DEPLOYMENT_CONFIG"))
    
    realroot_pkgs = deployment_config["realroot_packages"]
    deploy_realroot = deployment_config["deploy_realroot"]
    deploy_crossroot = deployment_config["deploy_crossroot"]
    pkglist_url = deployment_config["packagelisturl"]

    blog.info("Picked up deployment configuration")
    blog.info("==> Deploy realroot: {}".format(deploy_realroot))
    blog.info("==> Deploy crossroot: {}".format(deploy_crossroot))
    blog.info("==> Realroot packages: {}".format(realroot_pkgs))
    blog.info("==> PackagelistURL: {}".format(pkglist_url))
  
    # init leafcore
    if(buildenv.init_leafcore(pkglist_url) != 0):
        blog.info("Buildbot could not initialize leaf. Reporting system event.")
        bc.send_recv_msg("REPORT_SYS_EVENT {}".format("Buildbot setup failed because leaf is missing."))
        bc.disconnect()
        blog.info("Disconnected. Cannot continue.")
        return -1

    # check if the build environment is setup..
    blog.info("Checking build environments..")
    if(buildenv.check_buildenv(deploy_crossroot, deploy_realroot, realroot_pkgs) != 0):
        blog.info("Buildbot setup failed, because leaf failed to deploy the build environment. Reporting system event.")
        bc.send_recv_msg("REPORT_SYS_EVENT {}".format("Buildbot setup failed because leaf failed to deploy the build environment."))
        bc.disconnect()
        blog.info("Disconnected. Cannot continue.")
        return -1

    if (not buildenv.check_host_binary("chroot")):
        blog.error("'chroot' binary is missing. Reporting system event.")
        bc.send_recv_msg("REPORT_SYS_EVENT {}".format("Buildbot setup failed because the 'chroot' binary is missing."))
        bc.disconnect()
        blog.info("Disconnected. Cannot continue")
        return -1

    if (not buildenv.check_host_binary("strip")):
        blog.error("'strip' binary is missing. Reporting system event.")
        bc.send_recv_msg("REPORT_SYS_EVENT {}".format("Buildbot setup failed because the 'strip' binary is missing."))
        bc.disconnect()
        blog.info("Disconnected. Cannot continue")
        return -1

    # Signal readyness to server
    blog.info("Sending ready signal...")
    res = bc.send_recv_msg("SIG_READY")

    if(res == "CMD_OK"):
        blog.info("Server acknowleged ready signal.")
    else:
        blog.error("Server did not acknowledge ready signal. Exiting.")
        return -1

    # always wait for cmds from masterserver
    while True:
        blog.info("Waiting for commands from masterserver...")
        cmd = bc.recv_msg()
         
        # no data, server exited.
        if(cmd is None):
            blog.warn("Connection to server lost.")
            bc.disconnect
            return -1

        blog.debug("Handling command from server.. {}".format(cmd))

        res = None
        try:
            res = handleCommand.handle_command(bc, cmd)
        except Exception as ex:
            bc.send_recv_msg("REPORT_SYS_EVENT {}".format("Critical error. Cannot continue: {}".format(ex)))
            bc.disconnect()
            blog.error("Critcal error. Attempting to shutdown cleanly.")
            blog.error("Exception: {}".format(ex))
            blog.error("Traceback:")
            traceback.print_exc()
            buildenv.clean_env()
            return -1

        if(res == None):
            bc.send_recv_msg("REPORT_SYS_EVENT {}".format("Critical error. Attempting recovery.."))
            blog.error("Critical failure. Disconnecting..")
            bc.disconnect()
            blog.info("Attempting recovery..")
            buildenv.clean_env()
            blog.info("Dropping build environment..")
            buildenv.drop_buildenv()

            deployment_config = json.loads(bc.send_recv_msg("GET_DEPLOYMENT_CONFIG"))
            
            realroot_pkgs = deployment_config["realroot_packages"]
            deploy_realroot = deployment_config["deploy_realroot"]
            deploy_crossroot = deployment_config["deploy_crossroot"]

            blog.info("Recreating build environment..")
            buildenv.check_buildenv(deploy_crossroot, deploy_realroot, realroot_pkgs)
            blog.info("Reconnecting..")
            bc = branchclient.branchclient(server_address, int(server_port), identifier, authkey, "BUILD")
        else:
            res = bc.send_recv_msg(res)
            blog.debug("Result from server: {}".format(res))

if (__name__ == "__main__"):
    try:
        main()
    except KeyboardInterrupt:
        print()
        blog.info("Exiting on KeyboardInterrupt.")
        blog.info("Cleaning up..")
        buildenv.clean_env()
