# Branch - The AcaciaLinux package build system
# Copyright (c) 2021-2022 zimsneexh (https://zsxh.eu/)

import os
from log import blog

class branchOpts():
    def __init__(self, sftp_enable, sftp_ip, sftp_user, ssh_key, ssh_passphrase, sftp_workdir, web_subdir):
        self.sftp_enable = sftp_enable
        self.sftp_ip = sftp_ip
        self.sftp_user = sftp_user
        self.ssh_key = ssh_key
        self.ssh_passphrase = ssh_passphrase
        self.sftp_workdir = sftp_workdir
        self.web_subdir = web_subdir

def load_config():
    res = check_config()
    
    # User requested not to create a configuration file.. Quit
    if(check_config == -1):
        return -1

    home = os.environ['HOME'];
    conf_file = open("{}/.config/branch/branch.conf".format(home), "r")
    conf_arr = conf_file.read().split()

    options = branchOpts("", False, "", "", "", "", "")

    for prop in conf_arr:
        prop_arr = prop.split("=")
        key = prop_arr[0]

        if(len(prop_arr) != 2):
            blog.info("Invalid configuration file. Do you want to rerun the configuration assistant? (y/n).")
            answ = input()
            if(answ == "y"):
                reconf()
                return load_config()
            else:
                blog.error("Cannot continue with broken configuration file. Exiting.")
                return -1

        val = prop_arr[1]
        
        if(key == "sftp_enable"):
            if(val == "true"):
                options.sftp_enable = True
            else:
                options.sftp_enable = False
        elif(key == "sftp_ip"):
            options.sftp_ip = val
        elif(key == "sftp_user"):
            options.sftp_user = val
        elif(key == "ssh_key"):
            options.ssh_key = val
        elif(key == "ssh_passphrase"):
            options.ssh_passphrase = val
        elif(key == "sftp_workdir"):
            options.sftp_workdir = val
        elif(key == "web_subdir"):
            options.web_subdir = val

    return options

def reconf():
    home = os.environ['HOME'];
    blog.warn("Deleting configuration file..")
    
    os.remove("{}/.config/branch/branch.conf".format(home))
    return create_config()

def create_config():
    home = os.environ['HOME'];

    try:
        os.makedirs("{}/.config/branch".format(home))
    except FileExistsError:
        blog.info("Config directory already exists.")

    branch_cfg = open("{}/.config/branch/branch.conf".format(home), "w")
    sftp_support = False

    print("Do you want to enable sftp support? (y/n)")
    answ = input()
    if(answ.lower() == "y"):
        branch_cfg.write("sftp_enable=true\n")
        sftp_support = True
    else:
        branch_cfg.write("sftp_enable=false\n")


    if(sftp_support):
        print("Enter the Remote-Servers IP Address:")
        ip = input()
        branch_cfg.write("sftp_ip={}\n".format(ip)) 
        
        print("Enter remote username:")
        user = input()
        branch_cfg.write("sftp_user={}\n".format(user))

        print("Enter the SSH-Key location:")
        key_loc = input()
        branch_cfg.write("ssh_key={}\n".format(key_loc))

        print("WARNING: The SSH-key passphrase is stored in plain text! (Enter for none)")
        print("Enter the SSH-Key passphrase:")
        key_passphrase = input()
        branch_cfg.write("ssh_passphrase={}\n".format(key_passphrase))
        
        print("Enter sftp workdir: (Location where packages are stored on the webserver)")
        sftp_wkd = input()
        branch_cfg.write("sftp_workdir={}\n".format(sftp_wkd))

        print("Enter web subdirectory: (https://xy.xy/SUBDIRECTORY/example-package)")
        web_sub = input()
        branch_cfg.write("web_subdir={}\n".format(web_sub))

    blog.info("Configuration completed.")
    return 0

def check_config():
    config_exists = False
    home = os.environ['HOME'];

    try:
        config_exists = "branch.conf" in os.listdir("{}/.config/branch".format(home))
    except FileNotFoundError:
        config_exists = False

    if(not config_exists):
        print("No config file found. Do you want to create one? (y/n)")
        answ = input()
        if(answ.lower() == "y"):
            return create_config()
        else:
            blog.error("Cannot continue without config file. Exiting.") 
            return -1
