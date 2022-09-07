CONFIG_FILE = "/etc/branch/master.conf"

import os

from log import blog

class branch_options():
    # static class vars
    port = 27015
    httpport = 8080
    listenaddr = "127.0.0.1"
    debuglog = False
    untrustedclients = None


    # Loads the configuration file from disk and
    # sets the static class variables
    def load_config(self):
        self.check_config()
        
        conf_file = open(CONFIG_FILE, "r")
        conf_arr = conf_file.read().split("\n")

        for prop in conf_arr:
            if(len(prop) == 0):
                continue

            # skip comments
            if(prop[0] == '#'):
                continue
            
            prop_arr = prop.split("=")
            key = prop_arr[0]

            if(len(prop_arr) != 2):
                blog.error("Cannot continue with broken configuration file.")
                blog.error("Failed property: {}".format(prop))
                return -1

            val = prop_arr[1]
            if(key == "listenaddr"):
                self.listenaddr = val
            elif(key == "port"):
                self.port = val
            elif(key == "httpport"):
                self.httpport = val
            elif(key == "debuglog"):
                if(val == "False"):
                    self.debuglog = False
                else:
                    self.debuglog = True
            elif(key == "untrustedclients"):
                if(val == "False"):
                    self.untrustedclients = False
                else:
                    self.untrustedclients = True
            else:
                blog.warn("Skipping unknown configuration key: {}".format(key)) 


    def create_config(self):
        try:
            os.makedirs(os.path.dirname(CONFIG_FILE))
        except FileExistsError:
            pass

        branch_cfg = open(CONFIG_FILE, "w")
        
        # defaults
        branch_cfg.write("# IP address and port the server should listen on:\n")
        branch_cfg.write("listenaddr=127.0.0.1\n")
        branch_cfg.write("port=27015\n")
        branch_cfg.write("# Port the http server should listen on:\n")
        branch_cfg.write("httpport=8080\n")
        branch_cfg.write("# Print Debug log messages:\n")
        branch_cfg.write("debuglog=False\n")
        branch_cfg.write("# Disable client validation and allow untrusted clients to interact with the server:\n")
        branch_cfg.write("untrustedclients=False\n")

    def check_config(self):
        config_exists = False

        try:
            config_exists = "master.conf" in os.listdir(os.path.dirname(CONFIG_FILE))
        except FileNotFoundError:
            config_exists = False

        if(not config_exists):
            self.create_config()
