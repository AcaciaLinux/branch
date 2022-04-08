import os
import tarpkg
import lfpkg
import config
import pysftp

def push(options):
    if not(options.sftp_enable):
        print("Sftp support is currently disabled. Reconfigure with reconf option.")
        exit(0)

    if not("leaf.pkg" in os.listdir(os.getcwd())):
        print("This does not appear to be a package directory. Aborting.")
        exit(-1)

    leafpkg = lfpkg.parse()

    pwd = os.path.abspath(os.path.join(os.getcwd(), os.pardir))
    tar_name = "{}-{}.lfpkg".format(leafpkg.name, leafpkg.version)
    
    if not(tar_name in os.listdir(pwd)):
        print("{} does not have a package file.".format(pwd))
        print("Do you want to run pack? (y/n)")

        answ = input()
        if(answ.lower() == "y"):
            tarpkg.pack()
        else:
            exit(-1)

    #sftp
    sftp_con = pysftp.Connection(host=options.sftp_ip, username=options.sftp_user, private_key=options.ssh_key, private_key_pass=options.ssh_passphrase) 
    
    
