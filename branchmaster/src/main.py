# branch - The AcaciaLinux package build and distribution system
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

import threading
import blog

from branchweb import webserver
from branchweb import webauth
from config import config
from bsocket import server
from manager import manager
from localstorage import pkgbuildstorage
from localstorage import extrasourcestorage
from web import endpoints

def main():
    print("Branch (SERVER) - The AcaciaLinux package build / distribution system.")
    print("Copyright (c) zimsneexh 2022 (https://zsxh.eu/)")
    print("Version: "+ BRANCH_VERSION +" (" + BRANCH_CODENAME +")")
    print()
    print()
    
    

    blog.info("Masterserver initializing..")

    blog.info("Loading masterserver configuration..")
    if(config.config.setup() != 0):
        return -1

    if(config.config.get_config_option("Logger")["EnableDebugLog"] == "True"):
        blog.enable_debug_level()
        blog.debug("Debug log enabled.")

    listen_addr = config.config.get_config_option("Masterserver")["ListenAddress"]   
    listen_port = config.config.get_config_option("Masterserver")["ServerPort"]
    http_port = config.config.get_config_option("HTTPServer")["HTTPPort"]

    blog.info("Setting up webserver configuration..")   
    webserver.WEB_CONFIG["logger_function_debug"] = blog.debug
    webserver.WEB_CONFIG["logger_function_info"] = blog.web_log
    webserver.WEB_CONFIG["web_debug"] = config.config.get_config_option("Logger")["EnableDebugLog"] == "True" 
    webserver.WEB_CONFIG["send_cors_headers"] = config.config.get_config_option("HTTPServer")["SendCorsHeaders"] == "True"

    blog.info("Setting up user manager..")
    webauth.web_auth.setup_user_manager()

    blog.info("Registering webserver endpoints..")
    webserver.web_server.register_get_endpoints(
            endpoints.branch_web_providers.get_get_providers())
    webserver.web_server.register_post_endpoints(
            endpoints.branch_web_providers.get_post_providers())
    
    blog.info("Setting up local Packagebuild database..")
    pkgbuildstorage.storage.populate()

    blog.info("Setting up local Extrasource database..")
    extrasourcestorage.storage.populate()
    
    blob = extrasourcestorage.storage.get_extra_source_blob_by_id("a8a9308e-3283-43d3-9f97-10c365ad92ea")
    print(blob)

    web_thread = None
    if(config.config.get_config_option("HTTPServer")["EnableWebServer"] == "True"):
        blog.info("Launching webserver daemon on {} port {}..".format(listen_addr, http_port))
        web_thread = threading.Thread(target=webserver.start_web_server, daemon=True, args=(listen_addr, int(http_port)))
        try:
            web_thread.start()
        except Exception as ex:
            blog.error("Webserver failed to start: {}".format(ex))
    else:
        blog.warn("Webserver disabled by configuration option.")

    blog.info("Launching socket server..")
    blog.info("Serving on {} port {}".format(listen_addr, listen_port))

    cli_thread = threading.Thread(target=server.init_server, daemon=True, args=(listen_addr, int(listen_port)))
    try:
        cli_thread.start()
    except Exception as ex:
        blog.error("Socket server failed to start: {}".format(ex))
    
    blog.info("Branchmaster ready. Waiting for connections.")
    manager.manager.report_system_event("Branchmaster", "Ready for connections.")
    cli_thread.join()
    
    if(not web_thread is None):
        web_thread.join()


if (__name__ == "__main__"):
    try:
        main()
    except KeyboardInterrupt:
        print()
        blog.info("Exiting on keyboard interrupt..")
