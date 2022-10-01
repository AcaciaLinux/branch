BRANCH_CODENAME = "Route Kanal"
BRANCH_VERSION = "0.3"

B_TYPE = "CONTROLLER"

import argparse

from log import blog
from debugshell import debugshell
from commands import commands
from config import config
from bsocket import connect


def main():
    print("Branch (CONTROLLER) - The AcaciaLinux package build system.")
    print("Copyright (c) zimsneexh 2022 (https://zsxh.eu/)")
    print("Version: " + BRANCH_VERSION + " (" + BRANCH_CODENAME + ")")
    print()

    # load config
    blog.info("Loading configuration file..")
    conf = config.branch_options()

    if(conf.authkey == "NONE"):
        conf.authkey = None

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

    # parse arguments
    args = argparser.parse_args()

    # connect to server
    s = connect.connect(conf.serveraddr, conf.serverport, conf.identifier, conf.authkey, B_TYPE)

    if(s is None):
        blog.error("Connection refused.")
        return


    # check arguments
    if(args.debugshell):
        blog.info("Running debug shell!")
        debugshell.run_shell(s)
        exit(0)
    elif(args.submit):
        blog.info("Submitting package (current workdir).")
        commands.submit_package(s)
    elif(args.status):
        blog.info("Checkíng build status..")
        commands.build_status(s)
    elif(args.clientstatus):
        blog.info("Checking client status..")
        commands.client_status(s)
    elif(args.clearjobs):
        blog.info("Clearing completed jobs..")
        commands.clear_completed_jobs(s)
    elif(args.managedpackages):
        blog.info("Fetching managed packages..")
        commands.get_managed_packages(s)
    elif(args.managedpkgbuilds):
        blog.info("Fetching managed pkgbuilds..")
        commands.get_managed_pkgbuilds(s)
    elif(args.differencepkgs):
        blog.info("Fetching difference..")
        commands.get_diff_pkg(s)
    else:
        if(not args.checkout is None):
            blog.info("Checking out package '{}'.".format(args.checkout))
            commands.checkout_package(s, args.checkout)
        elif(not args.releasebuild is None):
            blog.info("Requesting release build for '{}'.".format(args.releasebuild))
            commands.release_build(s, args.releasebuild)
        elif(not args.crossbuild is None):
            blog.info("Requesting cross build for '{}'.".format(args.crossbuild))
            commands.cross_build(s, args.crossbuild)
        elif(not args.viewlog is None):
            blog.info("Requesting log for job id '{}'".format(args.viewlog))
            commands.get_buildlog(s, args.viewlog)

if (__name__ == "__main__"):
    try:
        main()
    except KeyboardInterrupt:
        print()
        blog.info("Exiting on KeyboardInterrupt.")
