import tarfile
import pycurl
import os
import subprocess
import shutil
import tarfile
import json
import datetime
import blog
import packagebuild
import leafpkg
import threading
import sys

from config import config
from buildenvmanager import buildenv
from bsocket import connect

EXECUTABLE_MAGIC_BYTES = b'\x7fELF'
SHARED_LIB_MAGIC_BYTES = b'\x7fELF'

#
# Handle a build request
# 
def handle_build_request(socket, cmd_body, use_crosstools):
    # Something went horribly wrong..
    if(cmd_body is None):
        blog.error("Received empty command body on PKG_BUILD request. Returning to ready-state.")
        connect.send_msg(socket, "BUILD_FAILED")
        buildenv.clean_env()
        return "SIG_READY"

    # Notify Overwatch
    connect.send_msg(socket, "JOB_ACCEPTED")
    
    # Setup buildenvironment
    if(buildenv.setup_env(use_crosstools)  == -1):
        connect.send_msg(socket, "BUILD_FAILED")
        connect.send_msg(socket, "REPORT_SYS_EVENT {}".format("Build failed because leaf failed to upgrade the real root. Reinstalling build environment."))
        buildenv.drop_buildenv()
        return None

    # Get rootdir from buildenv
    rootdir = buildenv.get_build_path()
    
    # create temp workdir directory
    builddir = os.path.join(rootdir, "branchbuild/")
    if(not os.path.exists(builddir)):
        os.mkdir(builddir)
    
    # parse the package build we got
    pkgbuild = packagebuild.package_build.from_json(cmd_body)
    blog.debug("Parsed package build is: {}".format(pkgbuild.get_json()))
    
    # validate..
    if(not pkgbuild.is_valid()):
        blog.warn("Invalid package build received from server. Rejected.")
        return "BUILD_FAILED"
    
    # build environment is setup, package build is ready.
    connect.send_msg(socket, "BUILD_ENV_READY")

    # get leafpkg
    lfpkg = leafpkg.leafpkg()
    lfpkg.name = pkgbuild.name
    lfpkg.version = pkgbuild.version
    lfpkg.real_version = pkgbuild.real_version
    lfpkg.description = pkgbuild.description
    lfpkg.dependencies = pkgbuild.dependencies

    # run build step
    if(build(builddir, pkgbuild, lfpkg, socket, use_crosstools) == "BUILD_COMPLETE"):
        connect.send_msg(socket, "BUILD_COMPLETE")
    else:
        connect.send_msg(socket, "BUILD_FAILED")
        buildenv.clean_env()
        return "SIG_READY"
    
    # lfpkg pkg_file creation..
    pkg_file = lfpkg.create_tar_package(builddir)
   
    # get file size
    file_size = os.path.getsize(pkg_file)
    blog.info("Package file size is {} bytes".format(file_size))
    
    res = connect.send_msg(socket, "FILE_TRANSFER_MODE {}".format(file_size))

    # if we got any other response, we couldn't switch mode
    if(not res == "ACK_FILE_TRANSFER"):
        blog.error("Server did not switch to file upload mode: {}".format(res))
        blog.error("Returning to ready-state.")
        connect.send_msg(socket, "BUILD_FAILED")

        buildenv.clean_env()
        return "SIG_READY"

    # send file over socket
    res = connect.send_file(socket, pkg_file)            
    
    # Check for mode switch
    if(res == "UPLOAD_ACK"):
        blog.info("File upload completed!")
    else:
        blog.error("Uploading the package file failed.")
        blog.error("Returning to ready-state")

        connect.send_msg(socket, "BUILD_FAILED")
        buildenv.clean_env()
        return "SIG_READY"

    
    # Clean build environment..
    buildenv.clean_env()
    connect.send_msg(socket, "BUILD_CLEAN")

    # We completed the build job. Send SIG_READY
    blog.info("Build job completed.")
    return "SIG_READY"


#
# Run a given pkgbuild 
#
def build(directory, package_build_obj, lfpkg, socket, use_crosstools):
    # directory we were called in, return after func returns
    call_dir = os.getcwd()
    # change to packagebuild directory
    os.chdir(directory)
    
    # create build_dir
    build_dir = os.path.join(directory, "build")
    os.mkdir(build_dir)

    # write leafpkg to disk
    destdir = lfpkg.write_package_directory()
   
    # change to build directory
    os.chdir(build_dir)

    if(package_build_obj.source):
        source_file = package_build_obj.source.split("/")[-1]
        
        blog.debug("Source file is: {}".format(source_file))

        out_file = open(source_file, "wb")

        blog.debug("Setting up pycurl..")
        curl = pycurl.Curl()
        curl.setopt(pycurl.URL, package_build_obj.source)
        curl.setopt(pycurl.FOLLOWLOCATION, 1)
        curl.setopt(pycurl.MAXREDIRS, 5)
        curl.setopt(pycurl.CONNECTTIMEOUT, 30)
        curl.setopt(pycurl.NOSIGNAL, 1)
        curl.setopt(pycurl.WRITEDATA, out_file)

        blog.info("Fetching source..")
        try:
            curl.perform()
        except Exception as ex:
            blog.error("Fetching source failed. {}".format(ex))
            os.chdir(call_dir)
            jlog = json.dumps(["Failed to fetch main source:", package_build_obj.source])
            res = connect.send_msg(socket, "SUBMIT_LOG {}".format(jlog))
            return "BUILD_FAILED"

        blog.info("Source fetched. File size on disk: {}".format(os.path.getsize(source_file)))

        out_file.close()
        curl.close()

        for extra_src in package_build_obj.extra_sources:
            blog.info("Fetching extra source: {}".format(extra_src))
            if(fetch_file(extra_src) != 0):
                os.chdir(call_dir)
                jlog = json.dumps(["Failed to fetch extra source:", extra_src])
                res = connect.send_msg(socket, "SUBMIT_LOG {}".format(jlog))
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
        if(package_build_obj.cross_dependencies == [ ]):
            blog.info("Falling back, no cross dependencies set. Installing 'build' dependencies: {}".format(package_build_obj.build_dependencies))
            if(buildenv.install_pkgs(package_build_obj.build_dependencies) != 0):
                os.chdir(call_dir)
                deps_failed = True
        else:
            blog.info("Installing 'cross' dependencies: {}".format(package_build_obj.cross_dependencies))
            if(buildenv.install_pkgs(package_build_obj.cross_dependencies) != 0):
                os.chdir(call_dir)
                deps_failed = True
    else:
        blog.info("Installing 'build' dependencies: {}".format(package_build_obj.build_dependencies))
        if(buildenv.install_pkgs(package_build_obj.build_dependencies) != 0):
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
        buildenv.clear_leaf_logs()
        return "BUILD_FAILED"

    blog.info("Package build will run in: {}".format(build_dir))
    blog.info("Package destination is: {}".format(destdir))
    
    blog.info("Writing build script to disk..")
    build_sh = open(os.path.join(build_dir, "build.sh"), "w")

    # set -e to cause script to exit once an error occurred
    build_sh.write("set -e\n")

    for line in package_build_obj.build_script:
        build_sh.write(line.strip())
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
    entry_sh.write("export PKG_NAME={}\n".format(package_build_obj.name))
    entry_sh.write("export PKG_VERSION={}\n".format(package_build_obj.version))
    entry_sh.write("export PKG_REAL_VERSION={}\n".format(package_build_obj.real_version))
    entry_sh.write("export PKG_INSTALL_DIR={}\n".format(chroot_destdir))
    entry_sh.write("./build.sh\n")
    entry_sh.close()

    # set executable bit on scripts
    os.system("chmod +x build.sh")
    os.system("chmod +x {}".format(entry_sh_path))

    blog.info("Chrooting to build environment...")
    blog.info("Build started on {}.".format(datetime.datetime.now()))

    blog.info("Building package...")
    std_out_str = ""
  
    proc = None

    if(config.config.get_config_option("BuildOptions")["RealtimeBuildlog"] == "True"):
        proc = subprocess.Popen(["chroot", temp_root, "/usr/bin/env", "-i", "HOME=root", "TERM=$TERM", "PATH=/usr/bin:/usr/sbin","/usr/bin/bash", "/entry.sh"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        std_output = [ ]
        
        def print_output_realtime(pipe):
            blog.info("BUILD LOG:")
            for line in iter(pipe.readline, ''):
                std_output.append(line)
                sys.stdout.write(line)

            blog.info("REALTIME LOG THREAD EXITING")

        t = threading.Thread(target=print_output_realtime, args=(proc.stdout,))
        t.start()
        
        proc.wait()
        t.join()

        for line in std_output:
            std_out_str = std_out_str + line

    else:
        proc = subprocess.run(["chroot", temp_root, "/usr/bin/env", "-i", "HOME=root", "TERM=$TERM", "PATH=/usr/bin:/usr/sbin","/usr/bin/bash", "/entry.sh"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

        # stdout log
        std_out_str = proc.stdout   


    # stdout log
    std_out = std_out_str.split("\n")

    # leaf log
    leaflog = buildenv.fetch_leaf_logs()
    leaflog_arr = leaflog.split("\n")

    # get last 5k lines of std_out
    std_out_trimmed = std_out[-5000:]

    # strip unneeded symbols from binaries
    stripped_files = [ ]
    if(proc.returncode == 0):
        stripped_files = strip(destdir)

    log = [ ]
    for line in leaflog_arr:
        log.append("[leaf] {}".format(line))

    for line in std_out_trimmed:
        log.append(line)

    for line in stripped_files:
        log.append("[strip] {}".format(line))

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

#
# Strips files in a given root_directory with ELF magic bytes
#
def strip(root_dir):
    blog.info("Stripping unneeded symbols from {}".format(root_dir))

    stripped_files = []

    for root, dir, files in os.walk(root_dir):
        for file in files:
            file_abs = os.path.join(root, file)
            
            # skip if symlink and dir
            if(not os.path.isfile(file_abs)):
                continue

            # get file magic bytes
            with open(file_abs, "rb") as f:
                magic_bytes = f.read(4)

                if(magic_bytes == EXECUTABLE_MAGIC_BYTES or magic_bytes == SHARED_LIB_MAGIC_BYTES):
                    blog.debug("[strip] Stripping file {}!".format(file_abs))
                    res = subprocess.run(["strip", "--strip-unneeded", file_abs], shell=False, capture_output=True)

                    if (res.returncode == 0):
                        blog.debug("[strip] {}".format(file_abs))
                        stripped_files.append(file_abs)
                else:
                    blog.debug("[strip] Skipped file {}, not ELF binary!".format(file_abs))

    return stripped_files

