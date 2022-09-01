CONFIG_FILE = "/etc/branch/master.conf"

import os

from log import blog

class branchOpts():
    port = None
    listenaddr = None
    debuglog = None
    untrustedclients = None

    def __init__(self):
        self.port = 0

# loads CONFIG_FILE from disk and parses it
# returns: 
#  0, parsing succesful
# -1, parsing failed.
def load_config():
    check_config()
    
    home = os.environ['HOME'];
    conf_file = open(CONFIG_FILE, "r")
    conf_arr = conf_file.read().split("\n")

    options = branchOpts()

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
            options.listenaddr = val
        elif(key == "port"):
            options.port = val
        elif(key == "debuglog"):
            if(val == "False"):
                options.debuglog = False
            else:
                options.debuglog = True
        elif(key == "untrustedclients"):
            if(val == "False"):
                options.untrustedclients = False
            else:
                options.untrustedclients = True
        else:
            blog.warn("Skipping unknown configuration key: {}".format(key)) 

    return options

def create_config():
    home = os.environ['HOME'];

    try:
        os.makedirs(os.path.dirname(CONFIG_FILE))
    except FileExistsError:
        pass

    branch_cfg = open(CONFIG_FILE, "w")
    
    # defaults
    branch_cfg.write("# IP address and port the server should listen on:\n")
    branch_cfg.write("listenaddr=127.0.0.1\n")
    branch_cfg.write("port=27015\n")
    branch_cfg.write("# Print Debug log messages:\n")
    branch_cfg.write("debuglog=False\n")
    branch_cfg.write("# Disable client validation and allow untrusted clients to interact with the server:\n")
    branch_cfg.write("untrustedclients=False\n")

def check_config():
    config_exists = False

    try:
        config_exists = "master.conf" in os.listdir(os.path.dirname(CONFIG_FILE))
    except FileNotFoundError:
        config_exists = False

    if(not config_exists):
        blog.info("First run detected. Continuing with default options.")
        create_config()

def load_config_file():
    check_config()
    conf_file = load_config()

    if(conf_file == -1):
        exit(-1)

    return conf_file

BRANCH_OPTIONS = load_config_file()
