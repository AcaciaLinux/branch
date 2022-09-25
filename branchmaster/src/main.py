BRANCH_CODENAME = "Route Kanal"
BRANCH_VERSION = "0.3"

import threading

from log import blog
from config import config
from bsocket import server
from manager import manager
from localstorage import pkgbuildstorage

from webserver import endpoints
from webserver import webserver

def main():
    print("Branch (SERVER) - The AcaciaLinux package build / distribution system.")
    print("Copyright (c) zimsneexh 2022 (https://zsxh.eu/)")
    print("Version: "+ BRANCH_VERSION +" (" + BRANCH_CODENAME +")")
    print()
    print()

    blog.info("Masterserver initializing..")

    blog.info("Loading masterserver configuration..")
    conf = config.branch_options()
    conf.load_config()

    blog.info("Launching webserver daemon on {} port {}..".format(conf.listenaddr, conf.httpport))
    endpoints.register_endpoints()
    thread = threading.Thread(target=webserver.start_web_server, daemon=True, args=(conf.listenaddr, int(conf.httpport)))

    thread.start()

    blog.info("Launching branchmaster..")
    blog.info("Serving on {} port {}".format(conf.listenaddr, conf.port))
    server.init_server(conf.listenaddr, int(conf.port)) 

if (__name__ == "__main__"):
    try:
        main()
    except KeyboardInterrupt:
        print()
        blog.info("Exiting on keyboard interrupt..")
