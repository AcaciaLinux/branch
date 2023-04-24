import os
import pycurl
import datetime
import subprocess
import time
from threading import Thread
import leafpkg
import tarfile

import blog
from branchclient import branchclient
from branchpacket import BranchRequest, BranchResponse, BranchStatus
from buildenvmanager import buildenv
from config.config import Config


ELF_MAGIC_BYTES=b'\x7fELF'
ELF_TYPE_EXE=b'\x02'
ELF_TYPE_DYN=b'\x03'


class Builder():
    """
    Initialized when we get a build request, destroyed
    right after
    """

    def __init__(self, bc: branchclient):
        blog.info("Initializing Builder..")

        self.bc = bc
        self.build_directory = os.path.join(buildenv.get_build_path(), "branchbuild/")


    def __del__(self):
        blog.info("Builder destroyed by runtime.")
        # TODO: do any cleanup needed here..

    def report_build_status_update(self, status: str) -> bool:
        """
        Report a build status update

        :param status: build status
        :return: True if UPDATE ack, False if not
        """
        buildstatus_response: BranchResponse = self.bc.send_recv_msg(BranchRequest("REPORTSTATUSUPDATE", status))

        match buildstatus_response.statuscode:
            case BranchStatus.OK:
                return True
            
            case other:
                return False

    def append_to_buildlog(self, update: list, print_locally=True) -> bool:
        """
        Append a list to the servers buildlog

        :param update: build log as list
        :return: True if log appended, False if not
        """
        if(update is None):
            return False

        buildlog_response: BranchResponse = self.bc.send_recv_msg(BranchRequest("APPENDLOG", update))

        # also print the log locally
        if(print_locally):
            for line in update:
                blog.info(line)

        match buildlog_response.statuscode:
            case BranchStatus.OK:
                return True
            
            case other:
                return False
            

    # TODO: add type annotation
    def build(self, pkgbuild: None, use_crosstools: bool) -> bool:
        """
        Run a build request

        """
        start_time = time.time()

        # initial status report
        self.report_build_status_update("JOB_ACCEPTED")
        self.append_to_buildlog([
            f"[Builder] Preparing to build package '{pkgbuild.name}'.",
            f"[Builder] Job started on {datetime.datetime.now()}.", 
             "[Builder] Build will run in 'crosstools' environment." if use_crosstools else "[Builder] Build will run in 'realroot' environment."
        ])

        blog.info("Acquiring deployment config..")
        deploymentconf_response: BranchResponse = self.bc.send_recv_msg(BranchRequest("GETDEPLOYMENTCONFIG", ""))
        match deploymentconf_response.statuscode:
        
            case BranchStatus.OK:
                deployment_config = deploymentconf_response.payload
                realroot_packages = deployment_config["realroot_packages"]
                deploy_realroot = deployment_config["deploy_realroot"]
                deploy_crossroot = deployment_config["deploy_crossroot"]

                self.append_to_buildlog([
                    "[Builder] Deployment configuration acquired.",
                    f"[Builder] Deployment configuration specifies '{realroot_packages}' as realroot.",
                    f"[Builder] Enabled environments are: Realroot={deploy_realroot}, Crossroot={deploy_crossroot}"
                ])

            case other:
                self.append_to_buildlog([
                    f"[Builder] Could not acquire deployment configuration: {deploymentconf_response.payload}",
                    "[Builder] No possible action to take, aborting."
                ])
                self.report_build_status_update("BUILD_FAILED")
                return False

        # Setup buildenv
        if(not buildenv.check_buildenv(deploy_crossroot, deploy_realroot, realroot_packages)):
            blog.error("Could not setup buildenvironment.")
            self.append_to_buildlog([
                "[Builder] Could not setup buildenvironment.",
                "[Builder] No possible action to take, aborting."
            ])
            self.report_build_status_update("BUILD_FAILED")
            return False
        
        # Setup buildenvironment
        if(not buildenv.setup_env(use_crosstools)):
            self.bc.send_recv_msg(BranchRequest("REPORTSYSEVENT", "Build environment is damaged and cannot be used. Buildbot will be unavailable as the environment is redeployed."))
            buildenv.drop_buildenv()
            self.append_to_buildlog([
                "[Builder] Could not setup buildenvironment. Leaf failed to upgrade environment.",
                "[Builder] No possible action to take, aborting."
            ])
            self.report_build_status_update("BUILD_FAILED")
            return False
        
        if(not os.path.exists(self.build_directory)):
            blog.debug("Creating build directory.")
            os.mkdir(self.build_directory)

        if(not pkgbuild.is_valid()):
            self.append_to_buildlog([
                "[Builder] Critical: Packagebuild is invalid.",
                "[Builder] The packagebuild should not be invalid as it is validated by the server.",
                "[Builder] Make sure the server and client version matches.",
                "[Builder] No possible action to take, aborting."
            ])
            self.report_build_status_update("BUILD_FAILED")
            return False 
        
        # build environment is ready
        self.report_build_status_update("BUILD_ENV_READY")

        self.append_to_buildlog([
            "[Builder] Generating leafpkg",
            "[Builder] Creating build directory"
        ])

        lfpkg = leafpkg.leafpkg()
        lfpkg.name = pkgbuild.name
        lfpkg.version = pkgbuild.version
        lfpkg.real_version = pkgbuild.real_version
        lfpkg.description = pkgbuild.description
        lfpkg.dependencies = pkgbuild.dependencies
        
        build_sub_directory: str = os.path.join(self.build_directory, "build")
        os.mkdir(build_sub_directory)

        build_destdir: str = lfpkg.write_package_directory(build_sub_directory)
        self.report_build_status_update("FETCHING_SOURCES")

        if(pkgbuild.source):
            self.append_to_buildlog([
                "[Builder] Attempting to fetch main source.."
            ])
            
            # fetch the file
            source_file_path: str = self.fetch_file_http(pkgbuild.source)
            if(source_file_path is None):
                self.report_build_status_update("BUILD_FAILED")
                return False

            # try to extract the source
            if(tarfile.is_tarfile(source_file_path)):
                self.append_to_buildlog([
                    "[Builder] Source file is a tarfile. Attempting to extract.."
                ])
                
                try:
                    with tarfile.open(source_file_path, "r") as tar_file:
                        tar_file.extractall(build_sub_directory)

                except Exception as ex:
                    self.append_to_buildlog([
                        "[Builder] Could not extract main source.",
                        "[Builder] No possible action to take, aborting."
                    ])
                    return False

            else:
                self.append_to_buildlog([
                    "[Builder] Source file is not a tarfile. Will not extract."
                ])

        for extra_src in pkgbuild.extra_sources:
            blog.info("Attempting to fetch extra source: '{extra_src}'")

            if("http://" in extra_src or "https://" in extra_src):
                if(self.fetch_file_http(extra_src) is None):
                    self.report_build_status_update("BUILD_FAILED")
                    return False
            else:
                if(self.fetch_file_masterserver(extra_src) is None):
                    self.report_build_status_update("BUILD_FAILED")
                    return False
                
        self.report_build_status_update("INSTALLING_DEPENDENCIES")

        if(self.install_dependencies(pkgbuild, use_crosstools)):
            leaf_log: list = buildenv.fetch_leaf_logs().split("\n")
            prefix_leaf_log: list = []

            prefix_leaf_log.append("[Builder] Package install log: ")
            for line in leaf_log:
                # skip empty lines in log
                if(line == ""):
                    continue

                prefix_leaf_log.append(f"[Leaf] {line}")

            self.append_to_buildlog(prefix_leaf_log)

        else:
            self.append_to_buildlog([
                "[Builder] Could not install required packages to the selected build environment.",
                "[Builder] No possible action to take, aborting."
            ])
            return False
        
        build_script_path = os.path.join(build_sub_directory, "build.sh")
        self.append_to_buildlog([
            f"[Builder] Package build will run in: {build_sub_directory}",
            f"[Builder] Package destination is: {build_destdir}",
            f"[Builder] Will write build script to: {build_script_path}"
        ])

        with open(os.path.join(build_sub_directory, "build.sh"), "w") as build_sh:
            # set -e to cause script to exit once an error occurred
            build_sh.write("set -e\n")

            for line in pkgbuild.build_script:
                build_sh.write(line.strip())
                build_sh.write("\n")

            build_sh.write("set +e\n")
            build_sh.close()
        
        inside_chroot_destdir: str = build_destdir.replace(buildenv.get_build_path(), "")

        # entry script
        entry_sh_path = os.path.join(buildenv.get_build_path(), "entry.sh")
        with open(entry_sh_path, "w") as entry_sh:
            # export PKG_NAME, PKG_VERSION, PKG_REAL_VERSION, PKG_INSTALL_DIR and HOME
            entry_sh.write("cd /branchbuild/build/\n")
            entry_sh.write("export PKG_NAME={}\n".format(pkgbuild.name))
            entry_sh.write("export PKG_VERSION={}\n".format(pkgbuild.version))
            entry_sh.write("export PKG_REAL_VERSION={}\n".format(pkgbuild.real_version))
            entry_sh.write("export PKG_INSTALL_DIR={}\n".format(inside_chroot_destdir))
            entry_sh.write("export HOME=/root/\n")
            entry_sh.write("./build.sh\n")
            entry_sh.close()

        os.system("chmod +x {}".format(os.path.join(build_sub_directory, "build.sh")))
        os.system("chmod +x {}".format(entry_sh_path))

        self.append_to_buildlog([
            f"[Builder] Wrote build script to: {build_sub_directory}",
            "[Builder] Executable bit set.",
            "[Builder] Chrooting to build environment.."
        ])

        self.report_build_status_update("BUILDING")

        def read_stdout_pipe(pipe):
            """
            Read the stdout pipe and send an update
            packet every 10 lines
            """
            # TODO: add Config (check if realtime..)

            buffer: list = [ ]

            for line in iter(pipe.readline, ''):
                # push the next line to the buffer
                buffer.append(line.strip())

                # send an update packet
                if(len(buffer) == 10):
                    self.append_to_buildlog(buffer, print_locally=False)
                    buffer = [ ]

            # stdout stream closed, clear out buffer
            if(len(buffer) != 0):
                self.append_to_buildlog(buffer, print_locally=False)
                buffer = [ ]

        # chroot to the build env
        build_process = subprocess.Popen(["chroot", buildenv.get_build_path(), "/usr/bin/env", "-i", "HOME=root", "TERM=$TERM", "PATH=/usr/bin:/usr/sbin","/usr/bin/bash", "/entry.sh"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        std_out_thread: Thread = Thread(target=read_stdout_pipe, args=(build_process.stdout,))
        std_out_thread.start()

        # wait for the subprocess to complete
        build_process.wait()
        std_out_thread.join()

        completed_time = time.time()

        if(build_process.returncode != 0):
            self.append_to_buildlog([
                "[Builder] Package build failed.",
                f"[Builder] Build script execution took {completed_time - start_time} seconds."
            ])
            self.report_build_status_update("BUILD_FAILED")
            return False
        
        self.append_to_buildlog([
            "[Builder] Package build completed successfully.",
            f"[Builder] Build script execution took {round(completed_time - start_time, 3)} seconds.",
            "[Builder] Stripping binaries.."
        ])

        self.report_build_status_update("STRIPPING_BINARIES")
        self.strip(build_destdir)
        self.report_build_status_update("BUILD_COMPLETE")

        self.append_to_buildlog([
            "[Builder] Build job completed successfully.",
            "[Builder] Creating tar file.."
        ])

        pkg_file_path: str = lfpkg.create_tar_package(build_destdir)
        pkg_file_size: int = os.path.getsize(pkg_file_path)

        self.append_to_buildlog([
            f"[Builder] Created package file is '{pkg_file_size}' bytes.",
            "[Builder] Switching to file transfer mode."
        ])

        filetransfer_response: BranchResponse = self.bc.send_recv_msg(BranchRequest("FILETRANSFERMODE", pkg_file_size))
        match filetransfer_response.statuscode:

            case BranchStatus.OK:
                blog.info("Server switched to filetransfer mode.")

            case other:
                blog.error(f"Server did not switch to file transfer mode: {filetransfer_response.payload}")
                self.report_build_status_update("BUILD_FAILED")
                return False

        # send file over socket
        sendfile_response: BranchResponse = self.bc.send_file(pkg_file_path)        
        match sendfile_response.statuscode:

            case BranchStatus.OK:
                blog.info("File upload completed.")

            case other:
                blog.error("File upload failed.")
                self.report_build_status_update("BUILD_FAILED")
                return False

        self.append_to_buildlog([
            "[Builder] File upload completed.",
            "[Builder] Build job completed. Cleaning up.."
        ])

        # Clean build environment..
        self.report_build_status_update("CLEANING_BUILD_ENV")
        blog.info("Build job completed.")
        return True


    def install_dependencies(self, pkgbuild, use_crosstools: bool) -> bool:
        self.append_to_buildlog([
            "[Builder] Installing required dependencies to build environment.."
        ])

        if(use_crosstools):
            self.append_to_buildlog([
                "[Builder] Cross build dependencies selected."
            ])

            # fallback to build_dependencies if cross_dependencies are not set.
            if(pkgbuild.cross_dependencies == [ ]):
                self.append_to_buildlog([
                    "[Builder] Falling back to release build dependencies as no cross dependencies are set."
                ])
                if(not buildenv.install_pkgs(pkgbuild.build_dependencies)):
                    return False
            else:
                if(not buildenv.install_pkgs(pkgbuild.cross_dependencies)):
                    return False

        else:
            self.append_to_buildlog([
                "[Builder] Release build dependencies selected."
            ])
            if(not buildenv.install_pkgs(pkgbuild.build_dependencies)):
                return False
            
        return True

    def fetch_file_http(self, url: str) -> None | str:
        """
        Fetches a file from a remote HTTP server

        :param url: The url
        :return: source_file path if completed, None if failed 
        """
        build_sub_directory: str = os.path.join(self.build_directory, "build")
        source_file = os.path.join(build_sub_directory, url.split("/")[-1])
        
        curl = pycurl.Curl()
        curl.setopt(pycurl.URL, url)
        curl.setopt(pycurl.FOLLOWLOCATION, 1)
        curl.setopt(pycurl.MAXREDIRS, 5)
        curl.setopt(pycurl.CONNECTTIMEOUT, 30)
        curl.setopt(pycurl.NOSIGNAL, 1)

        with open(source_file, "wb") as out_file:
            curl.setopt(pycurl.WRITEDATA, out_file)

            blog.info(f"Downloading file '{source_file}' from '{url}'..")
            self.append_to_buildlog([f"[DL] Downloading file '{source_file}' from '{url}'.."])
            try:
                curl.perform()
                curl.close()
            except Exception as ex:
                blog.error(f"Could not fetch source: {ex}")
                self.append_to_buildlog([f"[DL] Could not fetch source: {ex}"])
                curl.close()
                return None

            self.append_to_buildlog([f"[DL] Source fetched to {source_file}. File size on disk is {os.path.getsize(source_file)} bytes."])

        return source_file

    def fetch_file_masterserver(self, esid: str) -> None | str:
        blog.info("Extra source is managed by masterserver. Acquiring information..")
        esrcinfo_response: BranchResponse = self.bc.send_recv_msg(BranchRequest("GETEXTRASOURCEINFO", esid))

        match esrcinfo_response.statuscode:
            case BranchStatus.OK:
                pass
            
            case other:
                blog.error(f"Could not find extrasource with ID '{esid}'.")
                self.append_to_buildlog([f"[DL] Could not fetch extrasource with ID '{esid}'"])
                return None

        esrc_info = esrcinfo_response.payload
        
        if(not "filename" in esrc_info or not "datalength" in esrc_info):
            blog.error(f"Could not find extrasource with ID '{esid}'.")
            self.append_to_buildlog([f"[DL] Could not fetch extrasource with ID '{esid}'."])
            return None

        target_filename: str = esrc_info["filename"]
        target_datalength: int = esrc_info["datalength"]

        self.append_to_buildlog([f"[DL] Fetched extra source information for '{esid}'. Filename is '{target_filename}', with size '{target_datalength}' bytes"])

        self.bc.send_msg(BranchRequest("FETCHEXTRASOURCE", esid))

        build_sub_directory: str = os.path.join(self.build_directory, "build")
        target_file = os.path.join(build_sub_directory, target_filename)

        self.bc.receive_file(target_file, target_datalength)
        self.append_to_buildlog([f"[DL] Extra '{esid}'sourced downloaded from server."])
        blog.info(f"Extra '{esid}'sourced downloaded from server.")
        return target_file
    
    def strip(self, root_dir: str) -> list:
        """
        Strips binaries from a given root_dir

        :param root_dir: Directory to strip
        :return:  List of all stripped files.
        """

        for root, _dir, files in os.walk(root_dir):
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
                            blog.debug(f"[strip] Stripping file {file_abs}!")
                            res = subprocess.run(["strip", file_abs], shell=False, capture_output=True)

                            if (res.returncode == 0):
                                blog.debug(f"[strip] {file_abs}")

                                self.append_to_buildlog([
                                    f"[strip] Stripped file '{file_abs}'."
                                ])

                        else:
                            blog.debug(f"[strip] Skipped file {file_abs}, an ELF, but not strippable (exe/dyn)!")


                    else:
                        blog.debug(f"[strip] Skipped file {file_abs}, not ELF binary!")