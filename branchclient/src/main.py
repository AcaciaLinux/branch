B_HOST = "127.0.0.1"
B_PORT = 27015
B_NAME = "debug-shell"
B_TYPE = "CONTROLLER"

from log import blog
from debugshell import debugshell
from package import package
import argparse

def main():
    print("Branch (CLIENT) - The AcaciaLinux package build system.")
    print("Copyright (c) zimsneexh 2022 (https://zsxh.eu/)")
    print("Version: 0.1 (Point Insertion)")
    print()

    # TODO:
    # CONFIG FOR PORT
    

    argparser = argparse.ArgumentParser(description="The AcaciaLinux package build system.")
    argparser.add_argument("-ds", "--debugshell", help="Runs a debugshell on the remote server.", action="store_true")
    argparser.add_argument("-c", "--checkout", help="Checks out a package build from the remote server.")
    argparser.add_argument("-s", "--submit", help="Submits a package build to the remote server.", action="store_true")
    
    args = argparser.parse_args()

    if(args.debugshell):
        blog.info("Running debug shell!")
        debugshell.run_shell()
        exit(0)
    elif(args.submit):
        blog.info("Submitting package (current workdir).")
        package.submit_package()
    else:
        if(not args.checkout is None):
            blog.info("Checking out package {}!".format(args.checkout))
            package.checkout_package(args.checkout) 

if (__name__ == "__main__"):
    try:
        main()
    except KeyboardInterrupt:
        print()
        blog.info("Exiting on KeyboardInterrupt.")
