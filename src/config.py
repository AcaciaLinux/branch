import os

def load_config():
    check_config()

def reconf():
    # todo reconfigure option
    print()

def create_config():
    os.makedirs("~/.config/branch")

    branch_cfg = open("~/.config/branch/branch.conf", "w")
    sftp_support = False


    print("Do you want to enable sftp support? (y/n)")
    answ = input()
    if(answ.lower() == "y"):
        branch_cfg.write("sftp_enable=true\n")
        sftp_support = True
    else:
        branch_cfg.write("sftp_enable=false\n")
        branch_cfg.write("sftp_ip=\n")
        branch_cfg.write("sftp_user=\n")


    if(sftp_support):
        print("Enter the SSH-Servers IP Address:")
        ip = input()
        branch_cfg.write("sftp_ip={}".format(ip)) 
        
        print("Enter a username:")
        user = input()
        branch_cfg.write("sftp_user={}".format(user))
     

def check_config():
    config_exists = False

    try:
        print("rogler")
        config_exists = "branch.conf" in os.listdir("~/.config/branch")
    except FileNotFoundError:
        config_exists = False

    if(not config_exists):
        print("No config file found. Do you want to create one? (y/n)")
        answ = input()
        if(answ.lower() == "y"):
            create_config()
        else:
            print("Cannot continue without config file. Exiting.") 
            exit(0)
    else:
        print("Config file found.")

        

