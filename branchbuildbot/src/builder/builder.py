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
import branchclient

from config import config
from buildenvmanager import buildenv

ELF_MAGIC_BYTES=b'\x7fELF'
ELF_TYPE_EXE=b'\x02'
ELF_TYPE_DYN=b'\x03'

#
# Handle a build request
# 
def handle_build_request(bc, cmd_body, use_crosstools):
    # Something went horribly wrong..
    if(cmd_body is None):
        blog.error("Received empty command body on PKG_BUILD request. Returning to ready-state.")
        bc.send_recv_msg("REPORT_STATUS_UPDATE BUILD_FAILED")
        buildenv.clean_env()
        return "SIG_READY"

    # Notify Overwatch
    bc.send_recv_msg("REPORT_STATUS_UPDATE JOB_ACCEPTED")
   
    # acquire new deployment config
    blog.info("Acquiring deployment config..")
    deployment_config = json.loads(bc.send_recv_msg("GET_DEPLOYMENT_CONFIG"))
    
    realroot_pkgs = deployment_config["realroot_packages"]
    deploy_realroot = deployment_config["deploy_realroot"]
    deploy_crossroot = deployment_config["deploy_crossroot"]

    buildenv.check_buildenv(deploy_crossroot, deploy_realroot, realroot_pkgs)

    # Setup buildenvironment
    if(buildenv.setup_env(use_crosstools)  == -1):
        bc.send_recv_msg("REPORT_STATUS_UPDATE BUILD_FAILED")
        bc.send_recv_msg("REPORT_SYS_EVENT {}".format("Build failed because leaf failed to upgrade the real root. Reinstalling build environment."))
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
        bc.send_recv_msg("REPORT_SYS_EVENT {}".format("Build failed. The received packagebuild is invalid."))
        return "BUILD_FAILED"
    
    # build environment is setup, package build is ready.
    bc.send_recv_msg("REPORT_STATUS_UPDATE BUILD_ENV_READY")

    # get leafpkg
    lfpkg = leafpkg.leafpkg()
    lfpkg.name = pkgbuild.name
    lfpkg.version = pkgbuild.version
    lfpkg.real_version = pkgbuild.real_version
    lfpkg.description = pkgbuild.description
    lfpkg.dependencies = pkgbuild.dependencies

    # run build step
    if(build(builddir, pkgbuild, lfpkg, bc, use_crosstools) == "REPORT_STATUS_UPDATE BUILD_COMPLETE"):
        bc.send_recv_msg("REPORT_STATUS_UPDATE BUILD_COMPLETE")
    else:
        bc.send_recv_msg("REPORT_STATUS_UPDATE BUILD_FAILED")
        buildenv.clean_env()
        return "SIG_READY"
    
    # lfpkg pkg_file creation..
    pkg_file = lfpkg.create_tar_package(builddir)
   
    # get file size
    file_size = os.path.getsize(pkg_file)
    blog.info("Package file size is {} bytes".format(file_size))
    
    res = bc.send_recv_msg("FILE_TRANSFER_MODE {}".format(file_size))

    # if we got any other response, we couldn't switch mode
    if(not res == "ACK_FILE_TRANSFER"):
        blog.error("Server did not switch to file upload mode: {}".format(res))
        blog.error("Returning to ready-state.")
        bc.send_recv_msg("REPORT_STATUS_UPDATE BUILD_FAILED")

        buildenv.clean_env()
        return "SIG_READY"

    # send file over socket
    res = bc.send_file(pkg_file)
    
    # Check for mode switch
    if(res == "UPLOAD_ACK"):
        blog.info("File upload completed!")
    else:
        blog.error("Uploading the package file failed.")
        blog.error("Returning to ready-state")

        bc.send_recv_msg("BUILD_FAILED")
        buildenv.clean_env()
        return "SIG_READY"

    
    # Clean build environment..
    buildenv.clean_env()
    bc.send_recv_msg("REPORT_STATUS_UPDATE BUILD_ENV_CLEAN")

    # We completed the build job. Send SIG_READY
    blog.info("Build job completed.")
    return "SIG_READY"


#
# Run a given pkgbuild 
#

# directory = build directory
def build(directory, package_build_obj, lfpkg, bc, use_crosstools):
    # create build_dir
    build_dir = os.path.join(directory, "build")
    os.mkdir(build_dir)

    # write leafpkg to disk
    destdir = lfpkg.write_package_directory(directory)

    # status update
    bc.send_recv_msg("REPORT_STATUS_UPDATE FETCHING_SOURCE")

    if(package_build_obj.source):
        source_file = fetch_file_http(build_dir, package_build_obj.source)
        if(not source_file):
            blog.warn("Could not fetch main source.")
            res = bc.send_recv_msg("SUBMIT_LOG {}".format(json.dumps(["Could not fetch main source."])))
            return "REPORT_STATUS_UPDATE DOWNLOAD_EXTRA_SRC_FAILED"

        try:
            # check if file is tarfile and extract if it is
            if(tarfile.is_tarfile(source_file)):
                blog.info("Source is a tar file. Extracting...")
                tar_file = tarfile.open(source_file, "r")
                tar_obj = tar_file.extractall(build_dir)
            else:
                blog.warn("Source is not a tar file. Manual extraction required in build script.")

        except Exception as ex:
            blog.error("Exception thrown while unpacking: {}".format(ex))
            return "REPORT_STATUS_UPDATE BUILD_FAILED"

    else:
        blog.warn("No source specified. Not fetching source.")

    for extra_src in package_build_obj.extra_sources:
        blog.info("Attempting to fetch extra source: {}".format(extra_src))

        # check if it starts with http or https
        if("http://" in extra_src or "https://" in extra_src):
            blog.info("Extra source is remote, using http..")
            if(not fetch_file_http(build_dir, extra_src) != 0):
                dl_log = json.dumps(["Failed to fetch extra source:", extra_src])
                res = bc.send_recv_msg("SUBMIT_LOG {}".format(dl_log))
                return "REPORT_STATUS_UPDATE BUILD_FAILED"
        
        # assume its a branch managed extra source
        else:
            blog.info("Extra source is managed by masterserver. Acquiring information..")
            esrc_info = bc.send_recv_msg("EXTRA_SOURCE_INFO {}".format(extra_src))
    
            if(esrc_info == "INV_EXTRA_SOURCE"):
                blog.error("Specified extra source does not exist on the remote server.")
                return "REPORT_STATUS_UPDATE BUILD_FAILED"
            elif(esrc_info == "EXCEPTION_RAISED"):
                dl_log = json.dumps(["Requesting extra source {} raised an exception.".format(extra_src)])
                res = bc.send_recv_msg("SUBMIT_LOG {}".format(dl_log))
                return "REPORT_STATUS_UPDATE BUILD_FAILED"
                

            esrc_info = json.loads(esrc_info)
            blog.info("Extra source information acquired. Filename: {} Filesize: {}".format(esrc_info["filename"], esrc_info["datalen"]))
            
            # TODO: Need a way to check response, though this shouldn't fail..
            bc.send_msg("FETCH_EXTRA_SOURCE {}".format(extra_src))

            target_file = os.path.join(build_dir, esrc_info["filename"])
            bc.receive_file(target_file, esrc_info["datalen"])
            blog.info("Extra sources fetched.")


    deps_failed = False
    bc.send_recv_msg("REPORT_STATUS_UPDATE INSTALLING_DEPS")
    
    blog.info("Installing dependencies to temproot..")
    if(use_crosstools):
        if(package_build_obj.cross_dependencies == [ ]):
            blog.info("Falling back, no cross dependencies set. Installing 'build' dependencies: {}".format(package_build_obj.build_dependencies))
            if(buildenv.install_pkgs(package_build_obj.build_dependencies) != 0):
                deps_failed = True
        else:
            blog.info("Installing 'cross' dependencies: {}".format(package_build_obj.cross_dependencies))
            if(buildenv.install_pkgs(package_build_obj.cross_dependencies) != 0):
                deps_failed = True
    else:
        blog.info("Installing 'build' dependencies: {}".format(package_build_obj.build_dependencies))
        if(buildenv.install_pkgs(package_build_obj.build_dependencies) != 0):
            deps_failed = True

    if(deps_failed):
        blog.warn("Aborting job because dependencies failed to install. Submitting leaflog as buildlog.")
        
        leaf_log = buildenv.fetch_leaf_logs()
        leaf_log_arr = leaf_log.split("\n")
        jlog = json.dumps(leaf_log_arr)

        res = bc.send_recv_msg("SUBMIT_LOG {}".format(jlog))
        if(res == "LOG_OK"):
            blog.info("Log upload completed.")
        else:
            blog.warn("Log upload failed.")
        
        blog.debug("Clearing leaf logs..")
        buildenv.clear_leaf_logs()
        return "REPORT_STATUS_UPDATE BUILD_FAILED"

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

    # export PKG_NAME, PKG_VERSION, PKG_REAL_VERSION, PKG_INSTALL_DIR and HOME
    entry_sh.write("cd /branchbuild/build/\n")
    entry_sh.write("export PKG_NAME={}\n".format(package_build_obj.name))
    entry_sh.write("export PKG_VERSION={}\n".format(package_build_obj.version))
    entry_sh.write("export PKG_REAL_VERSION={}\n".format(package_build_obj.real_version))
    entry_sh.write("export PKG_INSTALL_DIR={}\n".format(chroot_destdir))
    entry_sh.write("export HOME=/root/\n")
    entry_sh.write("./build.sh\n")
    entry_sh.close()

    # set executable bit on scripts
    os.system("chmod +x {}".format(os.path.join(build_dir, "build.sh")))
    os.system("chmod +x {}".format(entry_sh_path))

    blog.info("Chrooting to build environment...")
    blog.info("Build started on {}.".format(datetime.datetime.now()))

    blog.info("Building package...")
    std_out_str = ""
  
    proc = None

    bc.send_recv_msg("REPORT_STATUS_UPDATE BUILDING")
    
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

    blog.info("Build complete.")

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
        bc.send_recv_msg("REPORT_STATUS_UPDATE STRIP_BINS")
        stripped_files = strip(destdir)

    log = [ ]
    for line in leaflog_arr:
        log.append("[leaf] {}".format(line))

    for line in std_out_trimmed:
        log.append(line)

    for line in stripped_files:
        log.append("[strip] {}".format(line))

    jlog = json.dumps(log)

    res = bc.send_recv_msg("SUBMIT_LOG {}".format(jlog))
    if(res == "LOG_OK"):
        blog.info("Log upload completed.")
    else:
        blog.warn("Log upload failed.")

    if(proc.returncode != 0):
        blog.error("Package build script failed.")
        return "REPORT_STATUS_UPDATE BUILD_FAILED"

    blog.info("Build completed successfully.")
    return "REPORT_STATUS_UPDATE BUILD_COMPLETE"

#
# download a file from web
# 0 success
# -1 failure
#
def fetch_file_http(destdir, url):
    source_file = os.path.join(destdir, url.split("/")[-1])
    
    out_file = open(source_file, "wb")

    blog.info("Setting up pycurl..")
    curl = pycurl.Curl()
    curl.setopt(pycurl.URL, url)
    curl.setopt(pycurl.FOLLOWLOCATION, 1)
    curl.setopt(pycurl.MAXREDIRS, 5)
    curl.setopt(pycurl.CONNECTTIMEOUT, 30)
    curl.setopt(pycurl.NOSIGNAL, 1)
    curl.setopt(pycurl.WRITEDATA, out_file)

    blog.info("Downloading file..")
    try:
        curl.perform()
    except Exception as ex:
        blog.error("Fetching source failed. {}".format(ex))
        return False

    blog.info("Source fetched to {}. File size on disk: {}".format(source_file, os.path.getsize(source_file)))

    out_file.close()
    curl.close()
    return source_file

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
                magic_bytes = f.read(0x04) # First read the 4 magic bytes
        
                if (magic_bytes == ELF_MAGIC_BYTES):
                    # If this is an elf binary, read up until 0x10 (0x10 - 0x04 = 0x0C), discard that and use 0x11
                    f.read(0x0C)

                    elf_type = f.read(0x01)

                    if (elf_type == ELF_TYPE_EXE or elf_type == ELF_TYPE_DYN):
                        blog.debug("[strip] Stripping file {}!".format(file_abs))
                        res = subprocess.run(["strip", file_abs], shell=False, capture_output=True)

                        if (res.returncode == 0):
                            blog.debug("[strip] {}".format(file_abs))
                            stripped_files.append(file_abs)

                    else:
                        blog.debug("[strip] Skipped file {}, an ELF, but not strippable (exe/dyn)!".format(file_abs))


                else:
                    blog.debug("[strip] Skipped file {}, not ELF binary!".format(file_abs))

    return stripped_files

