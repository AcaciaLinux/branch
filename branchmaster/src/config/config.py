CONFIG_FILE = "/etc/branch/master.conf"

import os
from log import blog

class branch_options():
    # static class vars
    port = 27015
    httpport = 8080
    listenaddr = "127.0.0.1"
    debuglog = False
    untrustedclients = ""
    authkeys = [ ]

    init_completed = False

    def __init__(self):
        if(not branch_options.init_completed):
            self.load_config();
            branch_options.init_completed = True

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
                branch_options.listenaddr = val
            elif(key == "port"):
                branch_options.port = val
            elif(key == "httpport"):
                branch_options.httpport = val
            elif(key == "debuglog"):
                if(val == "False"):
                    branch_options.debuglog = False
                else:
                    branch_options.debuglog = True
            elif(key == "untrustedclients"):
                if(val == "False"):
                    branch_options.untrustedclients = False
                else:
                    branch_options.untrustedclients = True
            elif(key == "authkeys"):
                branch_options.authkeys = self.parse_str_array(val)
            else:
                blog.warn("Skipping unknown configuration key: {}".format(key)) 

    def parse_str_array(self, string):
        vals = [ ]
        buff = ""

        for c in string:
            if(c == ']'):
                vals.append(buff)
                buff = ""
            elif(not c == '['):
                buff = buff + c
        
        blog.debug("Parsed values: {}".format(vals))
        return vals

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
        branch_cfg.write("# List of auth keys: [a][b][c]\n")
        branch_cfg.write("authkeys=\n")

    def check_config(self):
        if(not os.path.exists(CONFIG_FILE)):
            blog.info("First run detected. Continuing with default options.")
            self.create_config()
