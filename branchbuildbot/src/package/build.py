import tarfile
import pycurl
import os
import subprocess
import shutil
import tarfile
import json
import datetime

from buildenvmanager import buildenv
from log import blog
from package import leafpkg

class BPBOpts():
    def __init__(self):
        self.name = ""
        self.version = ""
        self.real_version = ""
        self.dependencies = ""
        self.source = ""
        self.extra_sources = [ ]
        self.description = ""
        self.build_dependencies = ""
        self.build_script = [ ]

        self.job_id = "job"

    def get_json(self):
        return json.dumps(self.__dict__)

def build(directory, package_build):
    # directory we were called in, return after func returns
    call_dir = os.getcwd()
    # change to packagebuild directory
    os.chdir(directory)
    
    # create build_dir
    build_dir = os.path.join(directory, "build")
    os.mkdir(build_dir)

    # get leafpkg
    lfpkg = leafpkg.leafpkg()
    lfpkg.name = package_build.name
    lfpkg.version = package_build.version
    lfpkg.real_version = package_build.real_version
    lfpkg.description = package_build.description
    lfpkg.dependencies = package_build.dependencies
    
    # write leafpkg to disk
    destdir = leafpkg.write_leaf_package_directory(lfpkg)
   
    # change to build directory
    os.chdir(build_dir)
    print("====================================================")

    if(package_build.source):
        source_file = package_build.source.split("/")[-1]
        
        blog.debug("Source file is: {}".format(source_file))

        out_file = open(source_file, "wb")

        blog.info("Setting up pycurl..")
        curl = pycurl.Curl()
        curl.setopt(pycurl.URL, package_build.source)
        curl.setopt(pycurl.FOLLOWLOCATION, 1)
        curl.setopt(pycurl.MAXREDIRS, 5)
        curl.setopt(pycurl.CONNECTTIMEOUT, 30)
        curl.setopt(pycurl.TIMEOUT, 300)
        curl.setopt(pycurl.NOSIGNAL, 1)
        curl.setopt(pycurl.WRITEDATA, out_file)

        blog.info("Fetching source..")
        try:
            curl.perform()
        except Exception as ex:
            blog.error("Fetching source failed. {}".format(ex))
            os.chdir(call_dir)
            return "BUILD_FAILED"

        blog.info("Source fetched. File size on disk: {}".format(os.path.getsize(source_file)))

        out_file.close()
        curl.close()

        for extra_src in package_build.extra_sources:
            blog.info("Fetching extra source: {}".format(extra_src))
            if(fetch_file(extra_src) != 0):
                os.chdir(call_dir)
                return "BUILD_FAILED"

        try:
            # check if file is tarfile and extract if it is
            if(tarfile.is_tarfile(source_file)):
                blog.info("Source is a tar file. Extracting...")
                tar_file = tarfile.open(source_file, "r")
                tar_obj = tar_file.extractall(".")
            else:
                blog.warn("Source is not a tar file. Manual extraction required in build script..")

        except Exception as ex:
            blog.error("Exception thrown while unpacking: {}".format(ex))
            os.chdir(call_dir)
            return "BUILD_FAILED"
    else:
        blog.warn("No source specified. Not fetching source.") 
   
    blog.info("Installing dependencies to temproot..")
    if(buildenv.install_pkgs(parse_bpb_str_array(package_build.dependencies)) != 0):
        os.chdir(call_dir)
        return "BUILD_FAILED"

    if(buildenv.install_pkgs(parse_bpb_str_array(package_build.build_dependencies)) != 0):
        os.chdir(call_dir)
        return "BUILD_FAILED"


    print("====================================================")
    blog.info("Package build will run in: {}".format(build_dir))
    blog.info("Package destination is: {}".format(destdir))
    
    blog.info("Writing build script to disk..")
    build_sh = open(os.path.join(build_dir, "build.sh"), "w")

    # set -e to cause script to exit once an error occurred
    build_sh.write("set -e\n")

    for line in package_build.build_script:
        build_sh.write(line)
        build_sh.write("\n")

    build_sh.write("set +e\n")
    build_sh.close()

    temp_root = buildenv.get_build_path()
    
    chroot_destdir = destdir.replace(temp_root, "")

    # entry script
    entry_sh_path = os.path.join(temp_root, "entry.sh")
    entry_sh = open(entry_sh_path, "w")

    entry_sh.write("cd /branchbuild/build && PKG_INSTALL_DIR={} ./build.sh\n".format(chroot_destdir))
    entry_sh.close()

    # set executable bit on scripts
    os.system("chmod +x build.sh")
    os.system("chmod +x {}".format(entry_sh_path))

    blog.info("Chrooting to build environment...")
    blog.info("Build started on {}.".format(datetime.datetime.now()))

    proc = subprocess.run(["chroot", temp_root, "/usr/bin/bash", "/entry.sh"])

    print("====================================================")
    if(proc.returncode != 0):
        blog.error("Package build script failed.")
        os.chdir(call_dir)
        return "BUILD_FAILED"

    blog.info("Build completed successfully.")

    # change back to call_dir
    os.chdir(call_dir)
    return "BUILD_COMPLETE"

#
# download a file from web
# 0 success
# -1 failure
#
def fetch_file(url):
    source_file = url.split("/")[-1]
    out_file = open(source_file, "wb")

    blog.info("Setting up pycurl..")
    curl = pycurl.Curl()
    curl.setopt(pycurl.URL, url)
    curl.setopt(pycurl.FOLLOWLOCATION, 1)
    curl.setopt(pycurl.MAXREDIRS, 5)
    curl.setopt(pycurl.CONNECTTIMEOUT, 30)
    curl.setopt(pycurl.TIMEOUT, 300)
    curl.setopt(pycurl.NOSIGNAL, 1)
    curl.setopt(pycurl.WRITEDATA, out_file)

    blog.info("Downloading file..")
    try:
        curl.perform()
    except Exception as ex:
        blog.error("Fetching source failed. {}".format(ex))
        return -1

    blog.info("Source fetched. File size on disk: {}".format(os.path.getsize(source_file)))

    out_file.close()
    curl.close()
    return 0
    

def parse_build_json(json):
    BPBopts = BPBOpts()

    BPBopts.name = json_get_key(json, "name")
    BPBopts.real_version = json_get_key(json, "real_version")
    BPBopts.version = json_get_key(json, "version")
    BPBopts.source = json_get_key(json, "source")
    BPBopts.extra_sources = json_get_key(json, "extra_sources")
    BPBopts.description = json_get_key(json, "description")
    BPBopts.dependencies = json_get_key(json, "dependencies")
    BPBopts.build_dependencies = json_get_key(json, "build_dependencies")
    BPBopts.build_script = json_get_key(json, "build_script")
    return BPBopts

#
# Parses branchpackagebuild array formay:
# [a][b][c]
#
def parse_bpb_str_array(string):
    vals = [ ]
    buff = ""

    for c in string:
        if(c == ']'):
            vals.append(buff)
            buff = ""
        elif(not c == '['):
            buff = buff + c

    return vals

def json_get_key(json_obj, key):
    try:
        return json_obj[key]
    except KeyError:
        return "UNSET"

