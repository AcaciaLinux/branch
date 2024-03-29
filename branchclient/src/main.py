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

import argparse
import blog
import branchclient

from commands import commands
from config.config import Config

BRANCH_CODENAME = "The Northern Star"
BRANCH_VERSION = "0.6"

def main():
    print("Branch (CONTROLLER) - The AcaciaLinux package build system.")
    print("Copyright (c) zimsneexh 2022 (https://zsxh.eu/)")
    print("Version: " + BRANCH_VERSION + " (" + BRANCH_CODENAME + ")")
    print()

    # load config
    blog.info("Loading configuration file..")
    if(not Config.setup()):
        return

    if(Config.get_config_option("Logger")["EnableDebugLog"] == "True"):
        blog.enable_debug_level()
        blog.debug("Debug log enabled.")
    
    try:
        authkey = Config.get_config_option("Connection")["AuthKey"]
        server_address = Config.get_config_option("Connection")["ServerAddress"]
        server_port = Config.get_config_option("Connection")["ServerPort"]
        identifier = Config.get_config_option("Connection")["Identifier"]
    except KeyError as ex:
        blog.error(f"Configuration file invalid. Could not find configuration key: {ex}")
        return

    # replace authkey NONE with None
    if(authkey == "NONE"):
        authkey = None
    
    # init argparser
    argparser = argparse.ArgumentParser(description="The AcaciaLinux package build system.")
    argparser.add_argument("-c", "--checkout", help="Checks out a package build from the remote server.")
    argparser.add_argument("-s", "--submit", help="Submits a package build to the remote server.", action="store_true")
    argparser.add_argument("-rb", "--releasebuild", help="Requests a release package build from the build server.")
    argparser.add_argument("-cb", "--crossbuild", help="Requests a release package build from the build server.")
    argparser.add_argument("-vl", "--viewlog", help="Requests build log of a completed job")
    argparser.add_argument("-st", "--status", help="Requests a list of running / completed jobs from the server.", action="store_true")
    argparser.add_argument("-cs", "--clientstatus", help="Requests a list of clients connected to the server.", action="store_true")
    argparser.add_argument("-cj", "--clearjobs", help="Clears the completed jobs from the masterserver.", action="store_true")
    argparser.add_argument("-mp", "--managedpackages", help="Get list of managed packages", action="store_true")
    argparser.add_argument("-mk", "--managedpkgbuilds", help="Get list of managed packagebuilds.", action="store_true")
    argparser.add_argument("-dp", "--differencepkgs", help="Get difference between packagebuilds and packages.", action="store_true")
    argparser.add_argument("-caj", "--cancelalljobs", help="Cancels all currently queued jobs", action="store_true")
    argparser.add_argument("-cn", "--canceljob", help="Cancels a currently queued job.")
    argparser.add_argument("-sys", "--viewsyslog", help="Fetches buildbot system logs from the masterserver", action="store_true")
    argparser.add_argument("-vd", "--viewdependers", help="Fetches dependency tree for a given package")
    argparser.add_argument("-rd", "--rebuilddependers", help="Rebuild dependers of a given package")
    argparser.add_argument("-rbs", "--releasebuildsol", help="Submits a branch solution to the masterserver. (RELEASEBUILD)")
    argparser.add_argument("-cbs", "--crossbuildsol", help="Submits a branch solution to the masterserver. (CROSSBUILD)")
    argparser.add_argument("-e", "--edit", help="Edit a package build from the remote server")
    argparser.add_argument("-ex", "--export", help="Exports all managed pkgbuilds from the remote server") 
    argparser.add_argument("-im", "--import", help="Imports all pkgbuilds from a given folder") 
    argparser.add_argument("-ci", "--clientinfo", help="Get client information") 
    argparser.add_argument("-tes", "--transferextrasource", help="Transfer an extra source to the server")
    argparser.add_argument("-ves", "--viewextrasources", help="View all managed extra sources.", action="store_true")
    argparser.add_argument("-rmes", "--rmextrasource", help="Delete extra source from the server")

    # dictionary mapping arguments to functions
    arg_funcs = {
        "checkout": commands.checkout_package,
        "submit": commands.submit_package,
        "releasebuild": commands.release_build,
        "crossbuild": commands.cross_build,
        "viewlog": commands.get_buildlog,
        "status": commands.build_status,
        "clientstatus": commands.client_status,
        "clearjobs": commands.clear_completed_jobs,
        "managedpackages": commands.get_managed_packages,
        "managedpkgbuilds": commands.get_managed_pkgbuilds,
        "differencepkgs": commands.get_diff_pkg,
        "cancelalljobs": commands.cancel_all_queued_jobs,
        "canceljob": commands.cancel_queued_job,
        "viewsyslog": commands.view_sys_log,
        "viewdependers": commands.view_dependers,
        "rebuilddependers": commands.rebuild_dependers,
        "releasebuildsol": commands.submit_solution_rb,
        "crossbuildsol": commands.submit_solution_cb,
        "edit": commands.edit_pkgbuild,
        "export": commands.export,
        "import": commands._import,
        "clientinfo": commands.get_client_info,
        "transferextrasource": commands.transfer_extra_source,
        "viewextrasources": commands.view_extra_sources,
        "rmextrasource": commands.remove_extra_source
    }

    # parse arguments
    args = argparser.parse_args()

    # loop over the dictionary
    for arg, func in arg_funcs.items():
        # get the argument value
        arg_val = vars(args)[arg]
        
        #if arg_val is True, theres no arg
        if(arg_val is not None and arg_val is not False):
            
            # connect to server
            bc = branchclient.branchclient(server_address, int(server_port), identifier, authkey, "CONTROLLER")
            
            if(not bc.ready):
                return

            # compare arg_val to True, because a str is also "true"
            if(arg_val is True):
                func(bc)
                return
            
            func(bc, arg_val)
            return

if (__name__ == "__main__"):
    try:
        main()
    except KeyboardInterrupt:
        print()
        blog.info("Exiting on KeyboardInterrupt.")
