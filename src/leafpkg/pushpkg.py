# Branch - The AcaciaLinux package build system
# Copyright (c) 2021-2022 zimsneexh (https://zsxh.eu/)

import os
from leafpkg import tarpkg
from leafpkg import lfpkg
from config import config
from log import blog
import pysftp
from paramiko import AuthenticationException
from pkgbuild import build
from leafpkg import tarpkg

def push(options, sc):
    os_lsdir = os.listdir(os.getcwd())
    
    if("leaf.pkg" in os_lsdir):
        return push_lfpkg(options,sc)
    elif("package.bpb" in os_lsdir):
        return push_bpb(options,sc)
    else:
        blog.error("This does not appear to be a package build or package directory. Cannot continue")
        return -1

    return 0


def push_bpb(options, sc):
    bpb_root = os.getcwd()

    BPBopts = build.parseBuildFile()
    
    # check if package build file is broken / parse failed
    if(BPBopts == -1):
        return -1

    pkg_file = "{}.lfpkg".format(BPBopts.getPkgDirectory())
   
    if(not os.path.exists(pkg_file)):
        blog.error("Package file does not exist yet.")
        if(sc):
            blog.info("Automatically running pack step as you requested.")
            tarpkg.pack(sc)
        else:
            print("Do you want to run the pack step?")
            answ = input()
            if(answ == "y"):
                tarpkg.pack(sc)
            else:
                return -1
        

    # run push_lfpkg
    os.chdir(BPBopts.getPkgDirectory())
    push_lfpkg(options, sc)

    # change back to bpb_root
    os.chdir(bpb_root)

def push_lfpkg(options, sc):
    if not(options.sftp_enable):
        blog.error("Sftp support is currently disabled. Reconfigure with reconf option.")
        return -1


    leafpkg = lfpkg.parse("leaf.pkg")
    
    # get pwd
    pwd = os.path.abspath(os.path.join(os.getcwd(), os.pardir))
    tar_name = "{}-{}.lfpkg".format(leafpkg.name, leafpkg.version)
    
    # check if archive exists
    if(not os.path.exists(os.path.join(pwd, tar_name))):
        blog.error(".lfpkg file not found.")
        if(sc):
            blog.info("Automatically running pack step as you requested.")
            tarpkg.pack(sc)
        else:
            print("Do you want to run the pack step?")
            answ = input()
            if(answ == "y"):
                tarpkg.pack(sc)
            else:
                return -1
    
    #sftp
    blog.info("Connecting to repository server..")
    try:
        sftp_con = pysftp.Connection(host=options.sftp_ip, username=options.sftp_user, private_key=options.ssh_key, private_key_pass=options.ssh_passphrase) 
    except AuthenticationException:
        blog.error("Could not connect to the SSH Server. Authentication Failure.")
        return -1

    blog.info("Changing remote workdir to {}..".format(options.sftp_workdir))
    sftp_con.cwd(options.sftp_workdir)

    blog.info("Fetching current package list..")
    sftp_con.get("leaf.pkglist", localpath="/tmp/leaf.pkglist_temp")

    blog.info("Updating package list..")
    updatePkgList(leafpkg, options)
    
    blog.info("Uploading updated package list..")
    sftp_con.put("/tmp/leaf.pkglist")
    
    blog.info("Cleaning up...")
    os.remove("/tmp/leaf.pkglist")
    os.remove("/tmp/leaf.pkglist_temp")

    blog.info("Creating pkg subdir..")
    try:
        sftp_con.mkdir(leafpkg.name)
    except IOError:
        blog.warn("Package subdirectory already exists. Assuming update.")
    
    sftp_con.cwd(leafpkg.name)
    
    blog.info("Uploading package file..")
    sftp_con.put("../{}".format(tar_name))
    
    sftp_con.close()
    blog.info("Done uploading package file!")
    
    # back to build root
    os.chdir("..")

def updatePkgList(pkg_target, options):
    blog.info("Parsing current package list..")

    # old lfpkg file
    lfpkglist_file_old = open("/tmp/leaf.pkglist_temp", "r")
    lfpkglist_arr_old = lfpkglist_file_old.read().split("\n")

    # new lfpkg file
    lfpkglist_file_new = open("/tmp/leaf.pkglist", "w")

    for prop in lfpkglist_arr_old:
        prop_arr = prop.split(";")

        pkg_name = prop_arr[0]
        
        if(pkg_name == pkg_target.name):
            blog.info("Updating target package in pkglist...")
        elif(not pkg_name == ""):
            lfpkglist_file_new.write(prop)
            lfpkglist_file_new.write("\n")
             
    blog.info("Appending package to pkglist")
    tar_name = "{}-{}.lfpkg".format(pkg_target.name, pkg_target.version)

    url = "http://{}/{}/{}/{}".format(options.sftp_ip, options.web_subdir, pkg_target.name, tar_name)

    lfpkglist_file_new.write("{};{};{};{};{}\n".format(pkg_target.name, pkg_target.version, pkg_target.description, pkg_target.dependencies, url))
    lfpkglist_file_new.close()
    

