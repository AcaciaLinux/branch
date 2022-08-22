CONFIG_FILE = "/etc/branch/buildbot.conf"

import os

from log import blog

class branchOpts():
    serverport = None
    serveraddr = None
    debuglog = None
    authkey = None
    identifier = None

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
    conf_arr = conf_file.read().split("\n")

    options = branchOpts()
    
    for prop in conf_arr:
        # skip empty line
        if(len(prop) == 0):
            continue

        # skip comments
        if(prop[0] == '#'):
            continue

        prop_arr = prop.split("=")
        key = prop_arr[0]

        if(len(prop_arr) != 2):
            blog.error("Cannot continue with broken configuration file.")
            return -1

        val = prop_arr[1]
        if(key == "serveraddr"):
            options.serveraddr = val
        elif(key == "serverport"):
            options.serverport = int(val)
        elif(key == "debuglog"):
            if(val == "False"):
                options.debuglog = False
            else:
                options.debuglog = True
        elif(key == "authkey"):
            options.authkey = val

        elif(key == "identifier"):
            options.identifier = val
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
    branch_cfg.write("# IP address and port of the masterserver:\n")
    branch_cfg.write("serveraddr=127.0.0.1\n")
    branch_cfg.write("serverport=27015\n")

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

def check_config():
    if(not os.path.exists(CONFIG_FILE)):
        blog.info("First run detected. Continuing with default options.")
        create_config()
