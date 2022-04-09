import os
import tarpkg
import lfpkg
import config
import pysftp
from paramiko import AuthenticationException

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
    print("Connecting to repository server..")
    try:
        sftp_con = pysftp.Connection(host=options.sftp_ip, username=options.sftp_user, private_key=options.ssh_key, private_key_pass=options.ssh_passphrase) 
    except AuthenticationException:
        print("Could not connect to the SSH Server. Authentication Failure.")
        exit(0)

    print("Changing remote workdir to {}..".format(options.sftp_workdir))
    sftp_con.cwd(options.sftp_workdir)

    print("Fetching current package list..")
    sftp_con.get("leaf.pkglist", localpath="/tmp/leaf.pkglist_temp")

    print("Updating package list..")
    updatePkgList(leafpkg, options)
    
    print("Uploading updated package list..")
    sftp_con.put("/tmp/leaf.pkglist_new")
    
    print("Cleaning up...")
    os.remove("/tmp/leaf.pkglist_new")
    os.remove("/tmp/leaf.pkglist_temp")

    print("Creating pkg subdir..")
    sftp_con.mkdir(leafpkg.name)
    sftp_con.cwd(leafpkg.name)
    
    print("Uploading package file..")
    sftp_con.put("../{}".format(tar_name))
    
    sftp_con.close()
    print("Done!")

def updatePkgList(pkg_target, options):
    print("Parsing current package list..")

    # old lfpkg file
    lfpkglist_file_old = open("/tmp/leaf.pkglist_temp", "r")
    lfpkglist_arr_old = lfpkglist_file_old.read().split()

    # new lfpkg file
    lfpkglist_file_new = open("/tmp/leaf.pkglist_new", "w")

    for prop in lfpkglist_arr_old:
        prop_arr = prop.split(";")

        pkg_name = prop_arr[0]

        if(pkg_name == pkg_target.name):
            print("Updating target package in pkglist...")
        else:
            lfpkglist_file_new.write(prop)
            
    os.remove("/tmp/leaf.pkglist_temp")
    
    print("Appending package to pkglist") 
    tar_name = "{}-{}.lfpkg".format(pkg_target.name, pkg_target.version)
    url = "http://{}/packages/{}/{}".format(options.sftp_ip, options.web_subdir, tar_name)

    lfpkglist_file_new.write("{};{};{};{};{}\n".format(pkg_target.name, pkg_target.version, pkg_target.description, pkg_target.dependencies, url))
    lfpkglist_file_new.close()
    

