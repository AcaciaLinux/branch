import tarfile
import os
import subprocess
import shutil
import requests
import tarfile
from leafpkg import initpkg
from log import blog

class BPBOpts():
    def __init__(self):
        self.name = ""
        self.version = ""
        self.source = ""
        self.dependencies = ""
        self.description = ""
        self.build_dependencies = ""
        self.build_script = [ ]
    

def build():
    if not("package.bpb" in os.listdir(os.getcwd())):
        blog.error("This package does not contain a package build file (package.bpb). Aborting.")
        exit(-1)

    blog.info("package.bpb file found!")
    BPBopts = parseBuildFile() 
    destdir = initpkg.newpkg(BPBopts.name, BPBopts.version, BPBopts.description, BPBopts.dependencies)
   
    blog.info("Installing build dependencies: {}".format(BPBopts.build_dependencies))
    install_deps(BPBopts.build_dependencies)

    blog.info("Creating build directory..")    
    try:
        os.mkdir("build")
    except FileExistsError:
        blog.warn("Old build directory found. Removing..")
        shutil.rmtree("build")
        os.mkdir("build")

    os.chdir("build")

    if(BPBopts.source):
        try:
            source_request = requests.get(BPBopts.source, stream=True)
            source_file = BPBopts.source.split("/")[-1]

            # fetch sources
            blog.info("Fetching source:", source_file)
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
        except Exception:
            blog.error("Broken link in packagebuildfile. Not fetching source.")
    else:
        log.warn("No source specified. Not fetching source.")

    srcdir = os.getcwd()

    blog.info("Package make script will run in: " + srcdir)
    blog.info("Package destination is: " + destdir)
    print("=========================================================")
    blog.info("Running build script..")
    os.putenv("PKG_INSTALL_DIR", destdir)
    
    build_sh = open(os.path.join(os.getcwd(), "build.sh"), "w")
    for line in BPBopts.build_script:
        build_sh.write(line)
        build_sh.write("\n")
    build_sh.close()
    
    os.system("chmod +x build.sh")
    subprocess.run(["./build.sh", ""], shell=True)
    
    blog.info("Buildscript completed.")
    print("=========================================================")
    os.chdir("..")
    cleanBuildDir()

def cleanBuildDir():
    blog.info("Cleaning up..")
    shutil.rmtree("build")


def cleanAll():
    if not("package.bpb" in os.listdir(os.getcwd())):
        blog.error("This package does not contain a package build file (package.bpb). Aborting.")
        exit(-1)
   

    try:
        shutil.rmtree("build")
    except FileNotFoundError:
        blog.warn("No build directory found..")

    
    BPBopts = parseBuildFile()
    pkg_dir = "{}-{}".format(BPBopts.name, BPBopts.version)
    
    try:
        shutil.rmtree(pkg_dir)
    except FileNotFoundError:
        blog.warn("No package directory found..")

    try:
        os.remove("{}-{}.lfpkg".format(BPBopts.name, BPBopts.version))    
    except FileNotFoundError:
        blog.warn("No package file found..")

    blog.info("Done cleaning current workdirectory..")

def install_deps(build_dependencies):
    blog.warn("STUB: install deps..")

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
                exit(-1)

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
            elif(key == "build"):
                build_opts = True
    
    return BPBopts
