# Branch - The AcaciaLinux package build system
# Copyright (c) 2021-2022 zimsneexh (https://zsxh.eu/)

import tarfile
import os
from leafpkg import lfpkg
from log import blog
from pkgbuild import build

def pack(sc):
    os_lsdir = os.listdir(os.getcwd())

    if("leaf.pkg" in os_lsdir):
        return pack_lfpkg(sc)
    elif("package.bpb" in os_lsdir):
        return pack_bpb(sc)
        
    else:
        blog.error("This does not appear to be a package build or package directory. Cannot continue.")
        return -1

    return 0

def pack_bpb(sc):
    bpb_root = os.getcwd()

    # parse build file 
    BPBopts = build.parseBuildFile()

    # check if package build file is broken / parse failed
    if(BPBopts == -1):
        return -1
    
    # change to leaf dir if it exists
    if(not os.path.exists(BPBopts.getPkgDirectory())):
        blog.error("Package is not built yet.")
        if(sc):
            print("Automatically running build script as you requested.")
            build.build(sc)
        else:
            print("Do you want to run the build script? (y/n)")
            answ = input()
            if(answ == "y"):
                build.build(sc)
            else:
                return -1

    # run pack_lfpkg()
    os.chdir(BPBopts.getPkgDirectory())
    pack_lfpkg(sc)

    # change back to bpb_root
    os.chdir(bpb_root)
    return 0

def pack_lfpkg(sc):
    # parse leafpkg
    leafpkg = lfpkg.parse("leaf.pkg")
    
    blog.info("Creating lfpkg file for {}...".format(leafpkg.name))

    # get pwd
    pwd = os.path.abspath(os.path.join(os.getcwd(), os.pardir))
    
    tar_name = "{}.lfpkg".format(leafpkg.getPkgDirectory())
    
    # delete old package files
    try:
        blog.info("Removing old package file..")
        os.remove(os.path.join(pwd, tar_name))
    except FileNotFoundError:
        blog.info("No old package file found.")

    # tar file with xz compression
    pkg_file_tar = tarfile.open(os.path.join(pwd, tar_name), "w:xz")
    
    # create tar file
    for root, dirs, files in os.walk(os.getcwd(), followlinks=False):
        for file in files:
            blog.info("Adding file: {}".format(os.path.join(root, file)))
            pkg_file_tar.add(os.path.join(root, file), os.path.relpath(os.path.join(root, file), os.path.join(os.getcwd(), '..')))
        for dir in dirs:
            if (len(os.listdir(os.path.join(root, dir))) == 0):
                blog.info("Adding dir: {}".format(os.path.join(root, dir)))
                pkg_file_tar.add(os.path.join(root, dir), os.path.relpath(os.path.join(root, dir), os.path.join(os.getcwd(), '..')))
            elif (os.path.islink(os.path.join(root, dir))):
                blog.info("Adding dirlink: {}".format(os.path.join(root, dir)))
                pkg_file_tar.add(os.path.join(root, dir), os.path.relpath(os.path.join(root, dir), os.path.join(os.getcwd(), '..')))

    pkg_file_tar.close()
    blog.info("Package file created in {}".format(pwd))
    return 0
