# Branch - The AcaciaLinux package build system
# Copyright (c) 2021-2022 zimsneexh (https://zsxh.eu/)

import tarfile
import os
import subprocess
import shutil
import requests
import tarfile
from leafpkg import initpkg
from leafpkg import lfpkg
from log import blog
from pyleaf import pyleafcore


class BPBOpts():
    def __init__(self):
        self.name = ""
        self.version = ""
        self.source = ""
        self.dependencies = ""
        self.description = ""
        self.build_dependencies = ""
        self.real_version = ""
        self.build_script = [ ]

    def getPkgDirectory(self):
        return "{}-{}".format(self.name, self.version)

def build(sc):
    if not("package.bpb" in os.listdir(os.getcwd())):
        blog.error("This package does not contain a package build file (package.bpb). Aborting.")
        return -1

    bpb_root = os.getcwd()

    # parse build file
    BPBopts = parseBuildFile() 
    
    # check if package build file is broken / parser failed
    if(BPBopts == -1):
        return -1

    # create leafpkg from packagebuild
    leafpkg = lfpkg.lfpkg(BPBopts.name, BPBopts.version, BPBopts.description, BPBopts.dependencies, BPBopts.real_version, "")
    pkg_root = os.path.join(os.getcwd(), leafpkg.getPkgDirectory())
    leafpkg.pkg_root = pkg_root

    # create pkg directory
    if(initpkg.newpkg(leafpkg) == 0):
        blog.warn("Package directory already exists.")
        if(sc):
            blog.info("Automatically removing as you requested.")
            shutil.rmtree(leafpkg.getPkgDirectory())
            initpkg.newpkg(leafpkg)
        else:
            print("Do you want to remove the existing package directory? (y/n)")
            answ = input()
            if(answ == "y"):
                blog.info("Removing..")
                shutil.rmtree(leafpkg.getPkgDirectory())
                initpkg.newpkg(leafpkg)
            else:
                return -1
    
    # install deps with pyleaf
    blog.info("Installing dependencies..")
    install_deps(BPBopts.build_dependencies, BPBopts.dependencies)

    # check if builddir exists and create / recreate
    blog.info("Creating build directory..")    
    try:
        os.mkdir("build")
    except FileExistsError:
        blog.warn("Old build directory found.")
        if(sc):
            blog.info("Automatically removing as you requested.")
            shutil.rmtree("build")
            os.mkdir("build")
        else:
            print("Do you want to remove the existing build directory? (y/n)")
            answ = input()
            if(answ == "y"):
                blog.info("Removing..")
                shutil.rmtree("build")
                os.mkdir("build")
            else:
                return -1

    # build directory is cwd()/build
    builddir = os.path.join(bpb_root, "build")
    os.chdir(builddir)
    
    # check if packagebuild has a source, if so, fetch it
    if(BPBopts.source):
        try:
            source_request = requests.get(BPBopts.source, stream=True)
            source_file = BPBopts.source.split("/")[-1]

            # fetch sources
            blog.info("Fetching source: " + source_file)
            out_file = open(source_file, "wb")
            shutil.copyfileobj(source_request.raw, out_file)

            # check if file is tarfile and extract if it is
            if(tarfile.is_tarfile(source_file)):
                blog.info("Source is a tar file. Extracting...")
                tar_file = tarfile.open(source_file, "r")
                tar_obj = tar_file.extractall(".")
            else:
                blog.warn("Source is not a tar file. Manual extraction required in build script..")
        
            blog.info("Source fetched")
        except Exception as ex:
            blog.error("Broken link in packagebuildfile. Not fetching source.")
    else:
        blog.warn("No source specified. Not fetching source.")


    destdir = os.path.join(leafpkg.pkg_root, "data")

    blog.info("Package build script will run in: " + builddir)
    blog.info("Package destination is: " + destdir)
    print("=========================================================")
    blog.info("Running build script..")
    blog.info("PKG_INSTALL_DIR={}".format(destdir))
    
    # environment variables
    os.putenv("PKG_INSTALL_DIR", destdir)
    
    # write build.sh file to build
    build_sh = open(os.path.join(builddir, "build.sh"), "w")
    for line in BPBopts.build_script:
        build_sh.write(line)
        build_sh.write("\n")
    build_sh.close()
    
    # set executable flag
    os.system("chmod +x build.sh")

    # run using subprocess
    subprocess.run(["./build.sh", ""], shell=True)
    
    blog.info("Buildscript completed.")
    print("=========================================================")

    # chdir to bpbroot
    os.chdir(bpb_root)

def install_deps(build_dependencies, dependencies):
    deps = []
    buff = ""

    # parse build deps
    for c in build_dependencies:
        if(c == ']'):
            deps.append(buff)
            buff = ""
        elif(not c == '['):
            buff = buff + c

    # parse regular deps
    for c in dependencies:
        if(c == ']'):
            deps.append(buff)
            buff = ""
        elif(not c == '['):
            buff = buff + c
    
    if(len(deps) == 0):
        blog.info("No dependencies provided.")
        return

    blog.info("Installing dependencies: {}".format(deps))
    leafcore = pyleafcore.Leafcore()
    leafcore.setVerbosity(2)
    leafcore.setRootDir("/")
    leafcore.a_update()
    leafcore.a_install(deps)
    blog.info("Dependency installation completed.")

def parseBuildFile():
    build_file = open("package.bpb", "r")
    build_arr = build_file.read().split("\n")

    BPBopts = BPBOpts()

    build_opts = False
    command = ""
    for prop in build_arr:
        if(build_opts):
            if(prop == "}"):
                build_opts = False
                continue
            
            # remove tab indentation
            prop = prop.replace("\t", "")
            
            # skip empty lines
            if(len(prop) == 0):
                continue;

            BPBopts.build_script.append(prop)
        else:
            prop_arr = prop.split("=")
            key = prop_arr[0]

            if(len(key) == 0):
                continue

            if(len(prop_arr) != 2):
                blog.error("Broken package build file. Failed property of key: ", key)
                return -1

            val = prop_arr[1]

            if(key == "name"):
                BPBopts.name = val
            elif(key == "version"):
                BPBopts.version = val
            elif(key == "source"):
                BPBopts.source = val
            elif(key == "dependencies"):
                BPBopts.dependencies = val
            elif(key == "description"):
                BPBopts.description = val
            elif(key == "builddeps"):
                BPBOpts.build_dependencies = val
            elif(key == "real_version"):
                BPBOpts.real_version = val
            
            # fetch build script until '}'
            elif(key == "build"):
                build_opts = True
    
    return BPBopts
