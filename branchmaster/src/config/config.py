CONFIG_FILE = "/etc/branch/master.conf"

import os
from log import blog

class branchOpts():
    port = None
    listenaddr = None
    debuglog = None

    def __init__(self):
        self.port = 0

# loads CONFIG_FILE from disk
# returns: 
# |  0, parsing succesful
# | -1, parsing failed.
def load_config():
    check_config()
    
    home = os.environ['HOME'];
    conf_file = open(CONFIG_FILE, "r")
    conf_arr = conf_file.read().split()

    options = branchOpts()

    for prop in conf_arr:
        prop_arr = prop.split("=")
        key = prop_arr[0]

        if(len(prop_arr) != 2):
            blog.error("Cannot continue with broken configuration file.")
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
    branch_cfg.write("listenaddr=127.0.0.1\n")
    branch_cfg.write("port=27015\n")
    branch_cfg.write("debuglog=False")    

def check_config():
    config_exists = False

    try:
        config_exists = "master.conf" in os.listdir(os.path.dirname(CONFIG_FILE))
    except FileNotFoundError:
        config_exists = False

    if(not config_exists):
        blog.info("First run detected. Continuing with default options.")
        create_config()
