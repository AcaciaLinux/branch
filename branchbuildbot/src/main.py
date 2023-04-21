"""
Branch - The AcaciaLinux package build system
Copyright (c) 2021-2022 zimsneexh (https://zsxh.eu/)
"""
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

BRANCH_CODENAME = "The Northern Star"
BRANCH_VERSION = "0.6"

import traceback
import branchclient
import blog

from branchpacket import BranchRequest, BranchResponse, BranchStatus
from handlecommand import handleCommand
from buildenvmanager import buildenv
from config.config import Config

def main():
    print("Branch (BUILDBOT) - The AcaciaLinux package build system.")
    print("Copyright (c) zimsneexh 2022 (https://zsxh.eu/)")
    print("Version: "+ BRANCH_VERSION +" (" + BRANCH_CODENAME +")")
    print()

    # load config
    blog.info("Loading configuration file..")
    if(not Config.setup()):
        return

    if(Config.get_config_option("Logger")["EnableDebugLog"] == "True"):
        blog.enable_debug_level()
        blog.debug("Debug log enabled.")

    authkey = Config.get_config_option("Connection")["AuthKey"]
    
    # replace authkey NONE with None
    if(authkey == "NONE"):
        authkey = None

    server_address = Config.get_config_option("Connection")["ServerAddress"]
    server_port = int(Config.get_config_option("Connection")["ServerPort"])
    identifier = Config.get_config_option("Connection")["Identifier"]

    # establish socket connection
    bc = branchclient.branchclient(server_address, int(server_port), identifier, authkey, "BUILD")

    if(not bc.ready):
        return

    # provide system performance metrics
    blog.info("Providing system information..")
    machineinfo_response: BranchResponse = bc.send_recv_msg(BranchRequest("SETMACHINEINFO", buildenv.get_host_info()))

    match machineinfo_response.statuscode:

        case BranchStatus.OK:
            blog.info("Machine information set.")

        case other:
            blog.error("Could not submit machine information: {}".format(deploymentconf_response.payload))
            return
    
    
    deploymentconf_response: BranchResponse = bc.send_recv_msg(BranchRequest("GETDEPLOYMENTCONFIG", ""))

    match deploymentconf_response.statuscode:
        
        case BranchStatus.OK:
            blog.info("Deployment configuration acquired.")

        case other:
            blog.error("Could not acquire deployment configuration: {}".format(deploymentconf_response.payload))
            return

    deployment_config = deploymentconf_response.payload
    
    if(not "realroot_packages" in deployment_config):
        blog.error("Received deployment configuration is invalid.")
        return

    if(not "deploy_realroot" in deployment_config):
        blog.error("Received deployment configuration is invalid.")
        return

    if(not "deploy_crossroot" in deployment_config):
        blog.error("Received deployment configuration is invalid.")
        return

    if(not "packagelisturl" in deployment_config):
        blog.error("Received deployment configuration is invalid.")
        return

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
    if(not buildenv.init_leafcore(pkglist_url)):
        blog.info("Buildbot could not initialize leaf. Reporting system event.")
        bc.send_recv_msg("REPORT_SYS_EVENT {}".format("Buildbot setup failed because leaf is missing."))
        bc.disconnect()
        blog.info("Disconnected. Cannot continue.")
        return

    # check if the build environment is setup..
    blog.info("Checking build environments..")
    if(not buildenv.check_buildenv(deploy_crossroot, deploy_realroot, realroot_pkgs)):
        blog.error("Buildbot setup failed, because leaf failed to deploy the build environment. Reporting system event.")
        
        bc.send_recv_msg(BranchRequest("REPORTSYSEVENT", "Buildbot setup failed because leaf failed to deploy the build environment."))
        bc.disconnect()
        
        blog.error("Disconnected. Cannot continue.")
        return

    # check if chroot binary is available
    if (not buildenv.check_host_binary("chroot")):
        blog.error("'chroot' binary is missing. Reporting system event.")
        
        bc.send_recv_msg(BranchRequest("REPORTSYSEVENT", "Buildbot setup failed because the 'chroot' binary is missing."))
        bc.disconnect()
        
        blog.error("Disconnected. Cannot continue")
        return

    # check if strip binary is available
    if (not buildenv.check_host_binary("strip")):
        blog.error("'strip' binary is missing. Reporting system event.")

        bc.send_recv_msg(BranchRequest("REPORTSYSEVENT", "Buildbot setup failed because the 'strip' binary is missing."))
        bc.disconnect()
        
        blog.info("Disconnected. Cannot continue")
        return

    # Send ready signal to server 
    blog.info("Sending ready signal...")
    
    sigready_response: BranchResponse = bc.send_recv_msg(BranchRequest("SIGREADY", ""))
    
    match sigready_response.statuscode:

        case BranchStatus.OK:
            blog.info("Server acknowledged ready signal.")
        
        case other:
            blog.error("Server did not acknowledge ready signal. Exiting.")
            return

    # always wait for cmds from masterserver
    while True:
        blog.info("Waiting for commands from masterserver...")
        recv_request: BranchRequest = bc.recv_branch_request()
         
        # no data, server exited.
        if(recv_request is None):
            blog.warn("Connection to server lost.")
            return

        # try to handle command
        try:
            res = handleCommand.handle_command(bc, recv_request)
        
        # recv_msg returns NoneType if Connection is lost, except it here
        except AttributeError:
            blog.warn("Connection to server lost")
            buildenv.clean_env()
            return
        
        # Except everything else as something else..
        except Exception as ex:
            bc.send_recv_msg("REPORT_SYS_EVENT {}".format("Critical error. Cannot continue: {}".format(ex)))
            bc.disconnect()
            blog.error("Critcal error. Attempting to shutdown cleanly.")
            blog.error("Exception: {}".format(ex))
            blog.error("Traceback:")
            traceback.print_exc()
            buildenv.clean_env()
            return
        
        if(res is None):
            continue

        if(res == "CRIT_ERR"):
            bc.send_recv_msg(BranchRequest("REPORTSYSEVENT", "Critical error while handling request. Attempting recovery.."))
            blog.error("Critical failure. Disconnecting..")
            bc.disconnect()
            blog.info("Attempting recovery..")
            buildenv.clean_env()
            blog.info("Dropping build environment..")
            buildenv.drop_buildenv()

            deploymentconf_response: BranchResponse = bc.send_recv_msg(BranchRequest("GETDEPLOYMENTCONFIG", ""))

            realroot_pkgs = deployment_config["realroot_packages"]
            deploy_realroot = deployment_config["deploy_realroot"]
            deploy_crossroot = deployment_config["deploy_crossroot"]
            pkglist_url = deployment_config["packagelisturl"]

            blog.info("Recreating build environment..")
            if(not buildenv.check_buildenv(deploy_crossroot, deploy_realroot, realroot_pkgs)):
                blog.error("Failed to deploy needed environment. Aborting.")
                return

            blog.info("Reconnecting..")
            bc = branchclient.branchclient(server_address, int(server_port), identifier, authkey, "BUILD")
            continue

        # send response back to the server.
        bc.send_msg(res)

if (__name__ == "__main__"):
    try:
        main()
    except KeyboardInterrupt:
        print()
        blog.info("Exiting on KeyboardInterrupt.")
        blog.info("Cleaning up..")
        buildenv.clean_env()
