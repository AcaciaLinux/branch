BRANCH_CODENAME = "A Red Letter Day"
BRANCH_VERSION = "0.2"

import threading

from log import blog
from config import config
from bsocket import server
from manager import manager
from localstorage import pkgbuildstorage

from webserver import endpoints
from webserver import webserver

BRANCH_OPTIONS = config.load_config()

def main():
    print("Branch (SERVER) - The AcaciaLinux package build / distribution system.")
    print("Copyright (c) zimsneexh 2022 (https://zsxh.eu/)")
    print("Version: "+ BRANCH_VERSION +" (" + BRANCH_CODENAME +")")
    print()
    print()

    blog.info("Masterserver initializing..")
    
    blog.info("Launching webserver...")
    endpoints.register_endpoints()
    
    # TODO!! config for httpport

    thread = threading.Thread(target=webserver.start_web_server, daemon=True, args=(BRANCH_OPTIONS.listenaddr, 8080))
    thread.start()

    blog.info("Launching branchmaster...")
    blog.info("Serving on {} port {}".format(BRANCH_OPTIONS.listenaddr, BRANCH_OPTIONS.port))
    server.init_server(BRANCH_OPTIONS.listenaddr, int(BRANCH_OPTIONS.port)) 
 
if (__name__ == "__main__"):
    try:
        main()
    except KeyboardInterrupt:
        print()
        blog.info("Exiting on keyboard interrupt..")
