BRANCH_CODENAME = "Point Insertion"
BRANCH_VERSION = "0.1"

B_TYPE = "CONTROLLER"

from log import blog
from debugshell import debugshell
from package import package
from config import config

import argparse

def main():
    print("Branch (CLIENT) - The AcaciaLinux package build system.")
    print("Copyright (c) zimsneexh 2022 (https://zsxh.eu/)")
    print("Version: " + BRANCH_VERSION + " (" + BRANCH_CODENAME + ")")
    print()

    # load config
    blog.info("Loading configuration file..")
    conf = config.load_config()

    if(conf.authkey == "NONE"):
        conf.authkey = None

    argparser = argparse.ArgumentParser(description="The AcaciaLinux package build system.")
    argparser.add_argument("-ds", "--debugshell", help="Runs a debugshell on the remote server.", action="store_true")
    argparser.add_argument("-c", "--checkout", help="Checks out a package build from the remote server.")
    argparser.add_argument("-s", "--submit", help="Submits a package build to the remote server.", action="store_true")
    argparser.add_argument("-rb", "--releasebuild", help="Requests a release package build from the build server.")
    
    args = argparser.parse_args()

    if(args.debugshell):
        blog.info("Running debug shell!")
        debugshell.run_shell(conf)
        exit(0)
    elif(args.submit):
        blog.info("Submitting package (current workdir).")
        package.submit_package(conf)
    else:
        if(not args.checkout is None):
            blog.info("Checking out package '{}'.".format(args.checkout))
            package.checkout_package(args.checkout)
        elif(not args.releasebuild is None):
            blog.info("Requesting release build for '{}'.".format(args.releasebuild))
            package.release_build(args.releasebuild)

if (__name__ == "__main__"):
    try:
        main()
    except KeyboardInterrupt:
        print()
        blog.info("Exiting on KeyboardInterrupt.")
