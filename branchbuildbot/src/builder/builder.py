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
from branchpacket import BranchRequest, BranchResponse, BranchStatus

ELF_MAGIC_BYTES=b'\x7fELF'
ELF_TYPE_EXE=b'\x02'
ELF_TYPE_DYN=b'\x03'

#
# Handle a build request
# 
def handle_build_request(bc, pkgbuild, use_crosstools) -> bool:
    # Notify Overwatch
    overwatch_response: BranchResponse = bc.send_recv_msg(BranchRequest("REPORTSTATUSUPDATE", "JOB_ACCEPTED"))
    match overwatch_response.statuscode:
        case BranchStatus.OK:
            blog.info("Job accepted. Overwatch notified.")

        case other:
            blog.error("Could not accept job.")
            bc.send_recv_msg(BranchRequest("REPORTSTATUSUPDATE", "BUILD_FAILED"))
            return False

    # acquire new deployment config
    blog.info("Acquiring deployment config..")
    
    deploymentconf_response: BranchResposne = bc.send_recv_msg(BranchRequest("GETDEPLOYMENTCONFIG", ""))
    match deploymentconf_response.statuscode:
        
        case BranchStatus.OK:
            blog.info("Deployment configuration acquired.")

        case other:
            blog.error("Could not acquire deployment configuration: {}".format(deploymentconf_response.payload))
            bc.send_recv_msg(BranchRequest("REPORTSTATUSUPDATE", "BUILD_FAILED"))
            return False

    deployment_config = deploymentconf_response.payload
    realroot_pkgs = deployment_config["realroot_packages"]
    deploy_realroot = deployment_config["deploy_realroot"]
    deploy_crossroot = deployment_config["deploy_crossroot"]
    pkglist_url = deployment_config["packagelisturl"]

    buildenv.check_buildenv(deploy_crossroot, deploy_realroot, realroot_pkgs)

    # Setup buildenvironment
    if(buildenv.setup_env(use_crosstools)  == -1):
        bc.send_recv_msg(BranchRequest("REPORTSYSEVENT", "Build failed because leaf failed to upgrade the real root. Reinstalling build environment."))
        buildenv.drop_buildenv()
        bc.send_recv_msg(BranchRequest("REPORTSTATUSUPDATE", "BUILD_FAILED"))
        return "CRIT_ERR"

    # Get rootdir from buildenv
    rootdir = buildenv.get_build_path()
    
    # create temp workdir directory
    builddir = os.path.join(rootdir, "branchbuild/")
    if(not os.path.exists(builddir)):
        os.mkdir(builddir)
    
    # validate..
    if(not pkgbuild.is_valid()):
        blog.warn("Invalid package build received from server. Rejected.")
        bc.send_recv_msg(BranchRequest("REPORTSYSEVENT", "Build failed. The received packagebuild could not be validated."))
        bc.send_recv_msg(BranchRequest("REPORTSTATUSUPDATE", "BUILD_FAILED"))
        return False 

    # build environment is setup, package build is ready.
    buildfailed_response: BranchResponse = bc.send_recv_msg(BranchRequest("REPORTSTATUSUPDATE", "BUILD_ENV_READY"))
        
    match buildfailed_response.statuscode:
        case BranchStatus.OK:
            blog.info("Server acknowledged status update.")

        case other:
            blog.error("Server did not acknowledge status update.")
            return False

    # get leafpkg
    lfpkg = leafpkg.leafpkg()
    lfpkg.name = pkgbuild.name
    lfpkg.version = pkgbuild.version
    lfpkg.real_version = pkgbuild.real_version
    lfpkg.description = pkgbuild.description
    lfpkg.dependencies = pkgbuild.dependencies

    # run build step
    if(build(builddir, pkgbuild, lfpkg, bc, use_crosstools)):
        bc.send_recv_msg(BranchRequest("REPORTSTATUSUPDATE","BUILD_COMPLETE"))
    else:
        bc.send_recv_msg(BranchRequest("REPORTSTATUSUPDATE","BUILD_FAILED"))
        buildenv.clean_env()
        return False 
    
    # lfpkg pkg_file creation..
    pkg_file = lfpkg.create_tar_package(builddir)
   
    # get file size
    file_size = os.path.getsize(pkg_file)
    blog.info("Package file size is {} bytes".format(file_size))
    
    filetransfer_response: BranchResponse = bc.send_recv_msg(BranchRequest("FILETRANSFERMODE", file_size))
    match filetransfer_response.statuscode:

        case BranchStatus.OK:
            blog.info("Server switched to filetransfer mode.")

        case other:
            blog.error("Server did not switch to file transfer mode: {}".format(filetransfer_response.payload))
            
            bc.send_recv_msg(BranchRequest("REPORTSTATUSUPDATE", "BUILD_FAILED"))
            buildenv.clean_env()
            return False

    # send file over socket
    sendfile_response: BranchResponse = bc.send_file(pkg_file)
    
    match sendfile_response.statuscode:

        case BranchStatus.OK:
            blog.info("File upload completed.")

        case other:
            blog.error("File upload failed.")
            bc.send_recv_msg(BranchRequest("REPORTSTATUSUPDATE", "BUILD_FAILED"))
            buildenv.clean_env()
            return False

    # Clean build environment..
    bc.send_recv_msg(BranchRequest("REPORTSTATUSUPDATE", "CLEANING_BUILD_ENV"))
    buildenv.clean_env()

    # We completed the build job. Send SIG_READY
    blog.info("Build job completed.")
    return True


#
# Run a given pkgbuild 
#
# directory = build directory
def build(directory, package_build_obj, lfpkg, bc, use_crosstools) -> bool:
    # create build_dir
    build_dir = os.path.join(directory, "build")
    os.mkdir(build_dir)

    # write leafpkg to disk
    destdir = lfpkg.write_package_directory(directory)

    # status update
    fetchsource_response: BranchResponse = bc.send_recv_msg(BranchRequest("REPORTSTATUSUPDATE", "FETCHING_SOURCES"))
    match fetchsource_response.statuscode:

        case BranchStatus.OK:
            blog.info("Server acknowledged status update.")
        
        case other:
            blog.error("Could not report status update.")
            return False

    if(package_build_obj.source):
        source_file = fetch_file_http(build_dir, package_build_obj.source)
        if(not source_file):
            blog.warn("Could not fetch main source.")
            status_response: BranchResponse = bc.send_recv_msg(BranchRequest("SUBMITLOG", ["Could not fetch main source."]))
            
            match status_response.statuscode:

                case BranchStatus.OK:
                    blog.info("Log upload completed.")

                case other:
                    blog.error("Could not update log.")
            
            return False
        
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
            status_response: BranchResponse = bc.send_recv_msg(BranchRequest("SUBMITLOG", ["Could not extract main source."]))
            
            match status_response.statuscode:

                case BranchStatus.OK:
                    blog.info("Log upload completed.")

                case other:
                    blog.error("Could not update log.")


            return False

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

                status_response: BranchResponse = bc.send_recv_msg(BranchRequest("SUBMITLOG", ["Could not fetch extrasource."]))
                
                match status_response.statuscode:

                    case BranchStatus.OK:
                        blog.info("Log upload completed.")

                    case other:
                        blog.error("Could not update log.")

                return False


        # assume its a branch managed extra source
        else:
            blog.info("Extra source is managed by masterserver. Acquiring information..")
            esrcinfo_response: BranchResponse = bc.send_recv_msg(BranchRequest("GETEXTRASOURCEINFO", extra_src))
            
            print(esrcinfo_response.payload)

            match esrcinfo_response.statuscode:

                case BranchStatus.OK:
                    pass
                
                case other:
                    blog.error("Could not find extrasource.")
                    status_response: BranchResponse = bc.send_recv_msg(BranchRequest("SUBMITLOG", ["Could not fetch extrasource with ID '{}'.".format(extra_src)]))
                    
                    match status_response.statuscode:
                        case BranchStatus.OK:
                            blog.info("Log upload completed.")

                        case other:
                            blog.error("Could not update log.")

                    return False

            esrc_info = esrcinfo_response.payload
            
            if(not "filename" in esrc_info):
                bc.send_recv_msg(BranchRequest("SUBMITLOG", ["Could not fetch extrasource with ID '{}'.".format(extra_src)]))
                return False

            if(not "datalength" in esrc_info):
                bc.send_recv_msg(BranchRequest("SUBMITLOG", ["Could not fetch extrasource with ID '{}'.".format(extra_src)]))
                return False

            target_filename: str = esrc_info["filename"]
            target_datalength: int = esrc_info["datalength"]

            blog.info("Extra source information acquired. Filename: {} Filesize: {}".format(target_filename, target_datalength))
            
            bc.send_msg(BranchRequest("FETCHEXTRASOURCE", extra_src))

            target_file = os.path.join(build_dir, target_filename)
            bc.receive_file(target_file, target_datalength)
            blog.info("Extra source '{}' fetched.".format(extra_src))


    deps_failed: bool = False

    # status update
    installdeps_response: BranchResponse = bc.send_recv_msg(BranchRequest("REPORTSTATUSUPDATE", "INSTALLING_DEPS"))
    match installdeps_response.statuscode:

        case BranchStatus.OK:
            blog.info("Server acknowledged status update.")
        
        case other:
            blog.error("Could not report status update.")
            return False

    
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
        status_response: BranchResponse = bc.send_recv_msg(BranchRequest("SUBMITLOG", leaf_log.split("\n")))
        
        match status_response.statuscode:
            case BranchStatus.OK:
                blog.info("Log upload completed.")

            case other:
                blog.error("Could not update log.")

        blog.debug("Clearing leaf logs..")
        buildenv.clear_leaf_logs()
        return False
        
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
  
    # status update
    installdeps_response: BranchResponse = bc.send_recv_msg(BranchRequest("REPORTSTATUSUPDATE", "BUILDING"))
    match installdeps_response.statuscode:

        case BranchStatus.OK:
            blog.info("Server acknowledged status update.")

        case other:
            blog.error("Could not report status update.")

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
        blog.info("Package build script completed successfully.")
        bc.send_recv_msg(BranchRequest("REPORTSTATUSUPDATE", "STRIP_BINS"))
        stripped_files = strip(destdir)
    else:
        blog.error("Package build script failed.")
        return False

    log = [ ]
    for line in leaflog_arr:
        log.append("[leaf] {}".format(line))

    for line in std_out_trimmed:
        log.append(line)

    for line in stripped_files:
        log.append("[strip] {}".format(line))

    status_response: BranchResponse = bc.send_recv_msg(BranchRequest("SUBMITLOG", log))

    match status_response.statuscode:
        case BranchStatus.OK:
            blog.info("Log upload completed.")

        case other:
            blog.error("Could not update log.")

    blog.info("Build completed successfully.")
    return True

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

