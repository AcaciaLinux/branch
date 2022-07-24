BRANCH_CODENAME = "Point Insertion"
BRANCH_VERSION = "0.1"

from log import blog
from config import config
from bsocket import server
from manager import manager
from localstorage import localstorage

def main():
    print("Branch (SERVER) - The AcaciaLinux package build system.")
    print("Copyright (c) zimsneexh 2022 (https://zsxh.eu/)")
    print("Version: "+ BRANCH_VERSION +" (" + BRANCH_CODENAME +")")
    print()

    blog.info("Masterserver initializing..")
    blog.info("Loading configuration file..")
    options = config.load_config()

    localstorage.check_storage()

    blog.info("Serving on {} port {}".format(options.listenaddr, options.port))
    server.init_server(options.listenaddr, int(options.port)) 
 

if (__name__ == "__main__"):
    try:
        main()
    except KeyboardInterrupt:
        print()
        blog.info("Exiting on keyboard interrupt..")
