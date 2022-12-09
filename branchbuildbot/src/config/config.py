CONFIG_FILE = "/etc/branch/buildbot.conf"

import os
from log import blog

class branch_options():
    serverport = 27015
    serveraddr = "127.0.0.1"
    leafpkglisturl = "http://127.0.0.1/?get=packagelist"
    debuglog = False
    authkey = ""
    identifier = ""

    init_completed = False

    def __init__(self):
        if(not branch_options.init_completed):
            if(self.load_config() == -1):
                branch_options.init_completed = False
            else:
                branch_options.init_completed = True
    
    # Loads the configuration file from disk and
    # sets the static class variables
    def load_config(self):
        self.check_config()
        
        conf_file = open(CONFIG_FILE, "r")
        conf_arr = conf_file.read().split("\n")

        for prop in conf_arr:
            # skip empty line
            if(len(prop) == 0):
                continue

            # skip comments
            if(prop[0] == '#'):
                continue


            divider = prop.find("=")
            key = prop[0:divider]
            val = prop[divider+1:len(prop)]

            if(val == ""):
                blog.error("Cannot continue with broken configuration file.")
                blog.error("Failed property: {}".format(prop))
                return -1
            
            if(key == "serveraddr"):
                branch_options.serveraddr = val
            elif(key == "serverport"):
                branch_options.serverport = int(val)
            elif(key == "leafpkglisturl"):
                branch_options.leafpkglisturl = val
            elif(key == "debuglog"):
                if(val == "False"):
                    branch_options.debuglog = False
                else:
                    branch_options.debuglog = True
            elif(key == "authkey"):
                if(val == "NONE"):
                    branch_options.authkey = None
                else:
                    branch_options.authkey = val
            elif(key == "identifier"):
                branch_options.identifier = val
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
        branch_cfg.write("# IP address and port of the masterserver:\n")
        branch_cfg.write("serveraddr=127.0.0.1\n")
        branch_cfg.write("serverport=27015\n")

        branch_cfg.write("# URL leaf should use to retrieve its packagelist\n")
        branch_cfg.write("leafpkglisturl=http://127.0.0.1/?get=packagelist\n")

        branch_cfg.write("# Print Debug log messages:\n")
        branch_cfg.write("debuglog=False\n")
        
        branch_cfg.write("# Authorization key to authenticate this client on the server:\n")
        branch_cfg.write("# Specify NONE if the server is running in\n")
        branch_cfg.write("# untrusted mode and doesn't validate clients.\n")
        branch_cfg.write("authkey=NONE\n")

        branch_cfg.write("# Client clear name:\n")
        branch_cfg.write("# Used to identify the client in the servers log.\n")
        branch_cfg.write("# (Should be unique)\n")
        branch_cfg.write("identifier=a-branch-client\n")

    def check_config(self):
        if(not os.path.exists(CONFIG_FILE)):
            blog.info("First run detected. Continuing with default options.")
            self.create_config()
