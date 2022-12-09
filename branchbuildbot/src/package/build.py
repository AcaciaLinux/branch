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
from bsocket import connect

class BPBOpts():
    def __init__(self):
        self.name = ""
        self.version = ""
        self.real_version = ""
        self.dependencies = ""
        self.build_dependencies = ""
        self.cross_dependencies = ""
        self.source = ""
        self.extra_sources = [ ]
        self.description = ""
        self.build_script = [ ]

        self.job_id = "job"

    def get_json(self):
        return json.dumps(self.__dict__)

def build(directory, package_build, socket, use_crosstools):
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

    deps_failed = False

    blog.info("Installing dependencies to temproot..")
    if(use_crosstools):
        if(package_build.cross_dependencies == ""):
            blog.info("Installing 'build' dependencies..")
            if(buildenv.install_pkgs(parse_bpb_str_array(package_build.build_dependencies)) != 0):
                os.chdir(call_dir)
                deps_failed = True
        else:
            blog.info("Installing 'cross' dependencies..")
            if(buildenv.install_pkgs(parse_bpb_str_array(package_build.cross_dependencies)) != 0):
                os.chdir(call_dir)
                deps_failed = True
    else:
        blog.info("Installing 'build' dependencies..")
        if(buildenv.install_pkgs(parse_bpb_str_array(package_build.build_dependencies)) != 0):
            os.chdir(call_dir)
            deps_failed = True

    if(deps_failed):
        blog.warn("Aborting job because dependencies failed to install. Submitting leaflog as buildlog.")
        
        leaf_log = buildenv.fetch_leaf_logs()
        leaf_log_arr = leaf_log.split("\n")
        jlog = json.dumps(leaf_log_arr)

        res = connect.send_msg(socket, "SUBMIT_LOG {}".format(jlog))
        if(res == "LOG_OK"):
            blog.info("Log upload completed.")
        else:
            blog.warn("Log upload failed.")
        
        blog.debug("Clearing leaf logs..")
        buildenv.fetch_leaf_logs()
        return "BUILD_FAILED"

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

    # export PKG_NAME, PKG_VERSION, PKG_REAL_VERSION and PKG_INSTALL_DIR
    entry_sh.write("cd /branchbuild/build/\n")
    entry_sh.write("export PKG_NAME={}\n".format(package_build.name))
    entry_sh.write("export PKG_VERSION={}\n".format(package_build.version))
    entry_sh.write("export PKG_REAL_VERSION={}\n".format(package_build.real_version))
    entry_sh.write("export PKG_INSTALL_DIR={}\n".format(chroot_destdir))
    entry_sh.write("./build.sh\n")
    entry_sh.close()

    # set executable bit on scripts
    os.system("chmod +x build.sh")
    os.system("chmod +x {}".format(entry_sh_path))

    blog.info("Chrooting to build environment...")
    blog.info("Build started on {}.".format(datetime.datetime.now()))

    blog.info("Building package...")
    proc = subprocess.run(["chroot", temp_root, "/usr/bin/env", "-i", "HOME=root", "TERM=$TERM", "PATH=/usr/bin:/usr/sbin","/usr/bin/bash", "/entry.sh"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    # stdout log
    std_out_str = proc.stdout
    std_out = std_out_str.split("\n")

    # leaf log
    leaflog = buildenv.fetch_leaf_logs()
    leaflog_arr = leaflog.split("\n")

    # get last 5k lines of std_out
    std_out_trimmed = std_out[-5000:]


    log = [ ]
    for line in leaflog_arr:
        log.append(line)

    for line in std_out_trimmed:
        log.append(line)
    
    jlog = json.dumps(log)

    res = connect.send_msg(socket, "SUBMIT_LOG {}".format(jlog))
    if(res == "LOG_OK"):
        blog.info("Log upload completed.")
    else:
        blog.warn("Log upload failed.")

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
    package_build = BPBOpts()

    package_build.name = json_get_key(json, "name")
    package_build.real_version = json_get_key(json, "real_version")
    package_build.version = json_get_key(json, "version")
    package_build.source = json_get_key(json, "source")
    package_build.extra_sources = json_get_key(json, "extra_sources")
    package_build.description = json_get_key(json, "description")
    package_build.dependencies = json_get_key(json, "dependencies")
    package_build.build_dependencies = json_get_key(json, "build_dependencies")
    package_build.cross_dependencies = json_get_key(json, "cross_dependencies")
    package_build.build_script = json_get_key(json, "build_script")
    return package_build

#
# Parses branchpackagebuild array format:
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

