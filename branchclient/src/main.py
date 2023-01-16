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

BRANCH_CODENAME = "Questionable Ethics"
BRANCH_VERSION = "0.5"

B_TYPE = "CONTROLLER"

import argparse
import blog

from debugshell import debugshell
from commands import commands
from config import config
from bsocket import connect

def main():
    print("Branch (CONTROLLER) - The AcaciaLinux package build system.")
    print("Copyright (c) zimsneexh 2022 (https://zsxh.eu/)")
    print("Version: " + BRANCH_VERSION + " (" + BRANCH_CODENAME + ")")
    print()

    # check for TERM var
    blog.initialize()

    # load config
    blog.info("Loading configuration file..")
    conf = config.branch_options()

    # check for valid conf
    if(not conf.init_completed):
        return -1

    if(conf.authkey == "NONE"):
        conf.authkey = None

    
    # connect to server
    s = connect.connect(conf.serveraddr, conf.serverport, conf.identifier, conf.authkey, B_TYPE)

    if(s is None):
        return

    # init argparser
    argparser = argparse.ArgumentParser(description="The AcaciaLinux package build system.")
    argparser.add_argument("-ds", "--debugshell", help="Runs a debugshell on the remote server.", action="store_true")
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
    argparser.add_argument("-vt", "--viewtree", help="Fetches dependency tree for a given package")
    argparser.add_argument("-rd", "--rebuilddependers", help="Rebuild dependers of a given package")
    argparser.add_argument("-rbs", "--releasebuildsol", help="Submits a branch solution to the masterserver. (RELEASEBUILD)")
    argparser.add_argument("-cbs", "--crossbuildsol", help="Submits a branch solution to the masterserver. (CROSSBUILD)")

    # dictionary mapping arguments to functions
    arg_funcs = {
        "debugshell": debugshell.run_shell,
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
        "viewtree": commands.view_tree,
        "rebuilddependers": commands.rebuild_dependers,
        "releasebuildsol": commands.submit_solution_rb,
        "crossbuildsol": commands.submit_solution_cb
    }

    # parse arguments
    args = argparser.parse_args()

    # loop over the dictionary
    for arg, func in arg_funcs.items():
        # get the argument value
        arg_val = vars(args)[arg]
        
        #if arg_val is True, theres no arg
        if(arg_val != None and arg_val != False):
            if(arg_val == True):
                func(s)
                return
            else:
                func(s, arg_val)
                return

if (__name__ == "__main__"):
    try:
        main()
    except KeyboardInterrupt:
        print()
        blog.info("Exiting on KeyboardInterrupt.")
