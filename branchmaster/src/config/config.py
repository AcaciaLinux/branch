CONFIG_FILE = "/etc/branch/master.conf"

import os
import blog

class branch_options():
    port = 27015
    httpport = 8080
    listenaddr = "127.0.0.1"
    send_cors_headers = False
    untrustedclients = ""
    authkeys = [ ]

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
            
            if(key == "listenaddr"):
                branch_options.listenaddr = val
            elif(key == "port"):
                branch_options.port = val
            elif(key == "httpport"):
                branch_options.httpport = val
            elif(key == "debuglog"):
                if(val == "False"):
                    branch_options.debuglog = False
                elif(val == "True"):
                    branch_options.debuglog = True
                else:
                    blog.error("Unknown configuration value.")

            elif(key == "untrustedclients"):
                if(val == "False"):
                    branch_options.untrustedclients = False
                elif(val == "True"):
                    branch_options.untrustedclients = True
                else:
                    blog.error("Unknown configuration value.")

            elif(key == "authkeys"):
                branch_options.authkeys = self.parse_str_array(val)
            elif(key == "send-cors-headers"):
                if(val == "False"):
                    branch_options.send_cors_headers = False
                elif (val == "True"):
                    branch_options.send_cors_headers = True
                else:
                    blog.error("Unknown configuration value.")
            

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
        branch_cfg.write("# Send '*' access control header to requesting clients (Should be disabled if nginx is in use.)\n")
        branch_cfg.write("send-cors-headers=False\n")

    def check_config(self):
        if(not os.path.exists(CONFIG_FILE)):
            blog.info("First run detected. Continuing with default options.")
            self.create_config()
