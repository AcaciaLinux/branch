import os
import uuid
import hashlib
import shutil

import blog
import packagebuild
from branchpacket import BranchRequest, BranchResponse, BranchStatus

import main
from bsocket import server
from manager.manager import Manager
from manager.job import Job
from dependency import dependency
from localstorage import packagestorage, pkgbuildstorage, extrasourcestorage
from overwatch import overwatch

def handle_command(branch_client, branch_request: BranchRequest) -> BranchResponse:

    match branch_client.client_type:
        case "CONTROLLER":
            return handle_command_controller(branch_client, branch_request)

        case "BUILD":
            return handle_command_buildbot(branch_client, branch_request)

        case "UNTRUSTED":
            return handle_command_untrusted(branch_client, branch_request)

        case other:
            return BranchResponse(BranchStatus.INTERNAL_SERVER_ERROR, "Invalid machine type assigned.")


def handle_command_untrusted(branch_client, branch_request: BranchRequest) -> BranchResponse:
    match branch_request.command:
        case "AUTH":
            blog.debug("Got authentication request from {}..".format(branch_client.get_identifier()))
            if(not "machine_identifier" in branch_request.payload):
                return BranchResponse(BranchStatus.REQUEST_FAILURE, "Required field 'machine_identifier' missing.")

            if(not "machine_type" in branch_request.payload):
                return BranchResponse(BranchStatus.REQUEST_FAILURE, "Required field 'machine_type' missing.")

            if(not "machine_authkey" in branch_request.payload):
                return BranchResponse(BranchStatus.REQUEST_FAILURE, "Required field 'machine_authkey' missing.")

            if(not "machine_version" in branch_request.payload):
                return BranchResponse(BranchStatus.REQUEST_FAILURE, "Required field 'machine_version' missing.")

            # unpack payload
            machine_identifier: str = branch_request.payload["machine_identifier"]
            machine_type: str = branch_request.payload["machine_type"]
            machine_authkey: str = branch_request.payload["machine_authkey"]
            machine_version: int = branch_request.payload["machine_version"]
            
            # Check if protocol version matches
            if(main.BRANCH_PROTOCOL_VERSION != machine_version):
                return BranchResponse(BranchStatus.REQUEST_FAILURE, f"Protocol version is not matching. Requested protocol {machine_version}, while the server only provides protocol {main.BRANCH_PROTOCOL_VERSION}.")
            
            # Check if authkey is valid
            if(Manager.is_authkey_valid(machine_authkey)):
                blog.info(f"Client authentication completed for '{branch_client.get_identifier()}'.")
            else:
                blog.warn(f"Client authentication failed for '{branch_client.get_identifier()}'.")
                return BranchResponse(BranchStatus.REQUEST_FAILURE, "Authkey is invalid.")
            
            # Check if identifier is valid
            if(branch_client.set_identifier(machine_identifier)):
                blog.info(f"Client with UUID '{branch_client.client_uuid}' is now known as '{branch_client.get_identifier()}'.") 
            else:
                return BranchResponse(BranchStatus.REQUEST_FAILURE, "Requested client name is not permitted.")

            # Check if machine type is valid
            if(branch_client.set_type(machine_type)):
                blog.info(f"Client type '{machine_type}' assigned to '{branch_client.get_identifier()}'.")
                
                # if the client is a buildbot, setup overwatch
                if(machine_type == "BUILD"):
                    overwatch.check_buildbot_alive(branch_client)

            else:
                return BranchResponse(BranchStatus.REQUEST_FAILURE, "Requested client type is invalid.")
            
            return BranchResponse(BranchStatus.OK, {
                "auth_status": "Authentication completed.",
                "logon_message": "Branchmaster v{} ({})".format(main.BRANCH_VERSION, main.BRANCH_CODENAME)
            })

        case other:
            return BranchResponse(BranchStatus.REQUEST_FAILURE, "Invalid command.")

def handle_command_controller(branch_client, branch_request: BranchRequest) -> BranchResponse:
    match branch_request.command:
        
        #
        # Checkout a package from the server.
        #
        case "CHECKOUT":
            pkg_build = pkgbuildstorage.storage.get_packagebuild_obj(branch_request.payload)
            
            if(pkg_build is None):
                return BranchResponse(BranchStatus.REQUEST_FAILURE, "Packagebuild not found.")
            
            blog.info("Client {} checked out package '{}'!".format(branch_client.get_identifier(), pkg_build.name))
            return BranchResponse(BranchStatus.OK, pkg_build.get_dict()) 
        
        #
        # Submit a package build to the server.
        #
        case "SUBMIT":
            try:
                pkgbuild = packagebuild.package_build.from_dict(branch_request.payload)
            except Exception:
                return BranchResponse(BranchStatus.REQUEST_FAILURE, "The submitted packagebuild could not be parsed.")
            
            if(not pkgbuild.is_valid()):
                return BranchResponse(BranchStatus.REQUEST_FAILURE, "The submitted packagebuild is invalid.")

            if(not pkgbuildstorage.storage.add_packagebuild_obj(pkgbuild)):
                return BranchResponse(BranchStatus.INTERNAL_SERVER_ERROR, "The submitted packagebuild could not be added to the database.")
            
            return BranchResponse(BranchStatus.OK, "Packagebuild submission accepted.")
        
        #
        # Request a release / cross build
        #
        case "BUILD":
            if(not "pkgname" in branch_request.payload):
                return BranchResponse(BranchStatus.REQUEST_FAILURE, "Missing request data: pkgname")

            if(not "buildtype" in branch_request.payload):
                return BranchResponse(BranchStatus.REQUEST_FAILURE, "Missing request data: buildtype")

            pkgbuild = pkgbuildstorage.storage.get_packagebuild_obj(branch_request.payload["pkgname"])
            
            if(pkgbuild is None):
                return BranchResponse(BranchStatus.REQUEST_FAILURE, "No such packagebuild")
            
            if(branch_request.payload["buildtype"] == "CROSS" and not Manager.deployment_config["deploy_crossroot"]):
                return BranchResponse(BranchStatus.REQUEST_FAILURE, "Could not request crossbuild, because the cross environment is disabled.")

            if(branch_request.payload["buildtype"] == "RELEASE" and not Manager.deployment_config["deploy_realroot"]):
                return BranchResponse(BranchStatus.REQUEST_FAILURE, "Could not request releasebuild, because the release environment is disabled.")

            job = Manager.get_queue().add_job(Job(branch_request.payload["buildtype"] == "CROSS", pkgbuild, branch_client.get_identifier()))
            Manager.get_scheduler().schedule()
            return BranchResponse(BranchStatus.OK, "Build request added to queue.")
        
        #
        # Get job log
        #
        case "GETJOBLOG":
            if(not "jobid" in branch_request.payload):
                return BranchResponse(BranchStatus.REQUEST_FAILURE, "Missing request data: jobid")

            if(not "offset" in branch_request.payload):
                return BranchResponse(BranchStatus.REQUEST_FAILURE, "Missing request data: offset")
            
            job = Manager.get_queue().get_job_by_id(branch_request.payload["jobid"])
            offset: int = branch_request.payload["offset"]

            if(job is None):
                return BranchResponse(BranchStatus.REQUEST_FAILURE, "No such job is available.")
            
            build_log = job.get_buildlog()
            if(build_log is None):
                return BranchResponse(BranchStatus.REQUEST_FAILURE, "No job log available.")
            
            # out of bounds
            if(len(build_log) < offset):
                return BranchResponse(BranchStatus.REQUEST_FAILURE, "Offset is out of bounds.")

            return BranchResponse(BranchStatus.OK, build_log[offset:len(build_log)])
        
        #
        # Get syslog
        #
        case "GETSYSLOG":
            return BranchResponse(BranchStatus.OK, Manager.system_events)

        #
        # Get dependers
        #
        case "GETDEPENDERS":
            names = pkgbuildstorage.storage.get_all_packagebuild_names()
            if(not branch_request.payload in names):
                return BranchResponse(BranchStatus.REQUEST_FAILURE, "Specified packagebuild does not exist.")

            release_dependers, cross_dependers = dependency.find_dependers(branch_request.payload, set(), False)
            
            all_dependers = {
                "releasebuild": list(release_dependers),
                "crossbuild": list(cross_dependers)
            }

            return BranchResponse(BranchStatus.OK, all_dependers)

        #
        # Rebuild all packages that depend on the specified package
        #
        case "REBUILDDEPENDERS":
            names = pkgbuildstorage.storage.get_all_packagebuild_names()
            pkgbuilds = pkgbuildstorage.storage.get_all_packagebuilds()
            
            if(not branch_request.payload in names):
                return BranchResponse(BranchStatus.REQUEST_FAILURE, "Specified packagebuild does not exist.")

            release_dependers, cross_dependers = dependency.find_dependers(branch_request.payload, set(), False)
            
            # cast from set -> list
            release_dependers = list(release_dependers)
            cross_dependers = list(cross_dependers)

            jobs = [ ]

            for dep in release_dependers:
                pkgbuild = pkgbuildstorage.storage.get_packagebuild_obj(dep)
                blog.info("Creating releasebuild job for {}".format(pkgbuild.name))
                
                # get a job obj, crosstools = False
                jobs.append(Job(False, pkgbuild, branch_client.get_identifier()))
            
            for dep in cross_dependers:
                pkgbuild = pkgbuildstorage.storage.get_packagebuild_obj(dep)
                blog.info("Creating crossbuild job for {}".format(pkgbuild.name))
                
                # get a job obj, crosstools = True
                jobs.append(Job(True, pkgbuild, branch_client.get_identifier()))
            
            Manager.get_queue().add_jobs(jobs)
            Manager.get_scheduler().schedule()
            return BranchResponse(BranchStatus.OK, "Rebuild dependers requested.")

        
        #
        # Get job status
        #
        case "GETJOBSTATUS":
            queued_jobs = Manager.get_queue().queued_jobs
            running_jobs = Manager.get_queue().running_jobs
            completed_jobs = Manager.get_queue().completed_jobs
            
            return BranchResponse(BranchStatus.OK, {
                "queuedjobs": [obj.get_info_dict() for obj in queued_jobs],
                "runningjobs": [obj.get_info_dict() for obj in running_jobs],
                "completedjobs": [obj.get_info_dict() for obj in completed_jobs]
            })

        #
        # Get connected clients
        #
        case "GETCONNECTEDCLIENTS":
            controllers = Manager.get_controller_names()
            buildbots = Manager.get_buildbot_names()
        
            return BranchResponse(BranchStatus.OK, {
                "controllers": controllers,
                "buildbots": buildbots
            })
        
        #
        # Get managed packages
        #
        case "GETMANAGEDPKGS":
            stor = packagestorage.storage()
            return BranchResponse(BranchStatus.OK, stor.packages)
        
        #
        # Get managed packagebuilds
        #
        case "GETMANAGEDPKGBUILDS":
            return BranchResponse(BranchStatus.OK, pkgbuildstorage.storage.get_all_packagebuild_names())
        
        #
        # Clear all completed jobs
        #
        case "CLEARCOMPLETEDJOBS":
            Manager.get_queue().clear_completed_jobs()
            return BranchResponse(BranchStatus.OK, "Completed jobs cleared.")
        
        #
        # Cancel all queued jobs
        #
        case "CANCELQUEUEDJOBS":
            Manager.get_queue().cancel_queued_jobs()
            return BranchResponse(BranchStatus.OK, "All queued jobs canceled.")
        
        #
        # Cancel a queued job by id
        #
        case "CANCELQUEUEDJOB":
            job = Manager.get_queue().get_job_by_id(branch_request.payload)
            
            if(job is None):
                return BranchResponse(BranchStatus.REQUEST_FAILURE, "No such job found")

            if(Manager.get_queue().cancel_queued_job(job.id)):
                return BranchResponse(BranchStatus.OK, "Job canceled successfully.")
            else:
                return BranchResponse(BranchStatus.REQUEST_FAILURE, "No such job.")

        #
        # Submit a solution for building
        #
        case "SUBMITSOLUTION":
            if(not "solution" in branch_request.payload):
                return BranchResponse(BranchStatus.REQUEST_FAILURE, "Missing request data: solution")

            if(not "buildtype" in branch_request.payload):
                return BranchResponse(BranchStatus.REQUEST_FAILURE, "Missing request data: buildtype")
            
            if(branch_request.payload["buildtype"] == "RELEASE" and not Manager.deployment_config["deploy_realroot"]):
                return BranchResponse(BranchStatus.REQUEST_FAILURE, "Release build environment is disabled or unavailable.")
 
            if(branch_request.payload["buildtype"] == "CROSS" and not Manager.deployment_config["deploy_crossroot"]):
                return BranchResponse(BranchStatus.REQUEST_FAILURE, "Cross build environment is disabled or unavailable.")


            if(branch_request.payload["solution"] == ""):
                return BranchResponse(BranchStatus.REQUEST_FAILURE, "Invalid solution.")
            
            jobs, status = dependency.job_arr_from_solution(branch_client, branch_request.payload["solution"], "CROSS" == branch_request.payload["buildtype"])
           
            if(jobs is None):
                return BranchResponse(BranchStatus.REQUEST_FAILURE, "Required package build '{}' is missing.".format(status))

            for job in jobs:
                Manager.get_queue().add_job(job)

            Manager.get_scheduler().schedule()
            return BranchResponse(BranchStatus.OK, "Solution queued.")
        
        #
        # Get all available client info
        #
        case "GETCLIENTINFO":
            target_client = Manager.get_client_by_name(branch_request.payload)

            if(target_client is None):
                return BranchResponse(BranchStatus.REQUEST_FAILURE, "No such client found.")

            return BranchResponse(BranchStatus.OK, target_client.get_sysinfo())
        
        #
        # Delete a package and packagebuild.
        #
        case "DELETEPKG":
            if(not branch_request.payload in pkgbuildstorage.storage.get_all_packagebuild_names()):
                return BranchResponse(BranchStatus.REQUEST_FAILURE, "No such packagebuild.")
            
            # cant delete crosstools if they are enabled
            if(branch_request.payload == "crosstools"):
                if(Manager.deployment_config["deploy_crossroot"]):
                    return BranchResponse(BranchStatus.REQUEST_FAILURE, "The requested package is enabled in the current deployment configuration. Cannot delete.")
            
            # cant delete realroot packages if they are enabled.
            if(branch_request.payload in Manager.deployment_config["realroot_packages"]):
                if(Manager.deployment_config["deploy_realroot"]):
                    return BranchResponse(BranchStatus.REQUEST_FAILURE, "The requested package is enabled in the current deployment configuration. Cannot delete.")

            blog.debug("Deleting packagebuild..")
            pkgbuildstorage.storage.remove_packagebuild(branch_request.payload)

            blog.debug("Deleting package..")
            
            # not locked, can delete
            if(not packagestorage.storage.check_package_lock(branch_request.payload)):
                packagestorage.storage().remove_package(branch_request.payload)
            else:
                blog.warn("Package requested for deletion is currently locked, added to deletion queue.")
                packagestorage.storage.deletion_queue.append(branch_request.payload)

            return BranchResponse(BranchStatus.OK, "Packagebuild deleted.")
        
        #
        # List of managed extra sources
        #
        case "GETMANAGEDEXTRASOURCES":
            managed_extra_sources: list = [obj.get_json() for obj in extrasourcestorage.storage.get_all_extrasources()]
            return BranchResponse(BranchStatus.OK, managed_extra_sources)
        
        #
        # Remove an extra soruce by ID
        #
        case "REMOVEEXTRASOURCE":
            if(extrasourcestorage.storage.remove_extrasource_by_id(branch_request.payload)):
                return BranchResponse(BranchStatus.OK, "Extra source removed.")
            
            return BranchResponse(BranchStatus.REQUEST_FAILURE, "Could not delete specified extra source.")
        
        #
        # Setup extra source transfer. 
        #
        case "TRANSFEREXTRASOURCE":
            if(not "filename" in branch_request.payload):
                return BranchResponse(BranchStatus.REQUEST_FAILURE, "Missing request data: filename")

            if(not "filedescription" in branch_request.payload):
                return BranchResponse(BranchStatus.REQUEST_FAILURE, "Missing request data: filedescription")

            if(not "filelength" in branch_request.payload):
                return BranchResponse(BranchStatus.REQUEST_FAILURE, "Missing request data: filelength")

            file_info = branch_request.payload
            byte_count = 0

            try:
                byte_count = int(file_info["filelength"])
            except Exception:
                return BranchResponse(BranchStatus.REQUEST_FAILURE, "'filelength' needs to be a valid integer.")
            
            _id = uuid.uuid4()
            desc = branch_request.payload["filedescription"]
            file_name = branch_request.payload["filename"]

            #
            # Extra Source pending class
            #
            class ExtraSourcePending():
                def __init__(self, client, _id, file_name, desc):
                    self.client = client
                    self.id = _id
                    self.desc = desc
                    self.file_name = file_name

            Manager.add_pending_extra_source(ExtraSourcePending(branch_client, _id, file_name, desc))

            branch_client.file_target = os.path.join(server.STAGING_AREA, "{}.es".format(_id))
            branch_client.file_target_bytes = byte_count
            branch_client.file_transfer_mode = True
            return BranchResponse(BranchStatus.OK, "Transfer setup.")
        
        #
        # Complete extra source transfer, commit package to database
        #
        case "COMPLETETRANSFER":
            pending_extra_src = None

            # find correct pending job
            for pes in Manager.get_pending_extra_sources():
                if(pes.client.client_uuid == branch_client.client_uuid):
                    pending_extra_src = pes
                    break
            
            target_file = os.path.join(server.STAGING_AREA, "{}.es".format(pending_extra_src.id))
            
            with open(target_file, "rb") as _file:
                _bytes = _file.read()

            if(not extrasourcestorage.storage.add_extrasource(str(pending_extra_src.id), pending_extra_src.file_name, pending_extra_src.desc, _bytes)):
                return BranchResponse(BranchStatus.REQUEST_FAILURE, "Could not insert to database.")
            
            # remove pending extra src
            Manager.remove_pending_extra_source(pending_extra_src)
            
            # delete staged extra sourcefile
            blog.info("Removing temporary file in staging directory..")
            try:
                os.remove(target_file)
            except Exception as ex:
                blog.warn("Could not delete temporary file: {}".format(ex))

            return BranchResponse(BranchStatus.OK, "File inserted to database.")

        #
        # Invalid commands
        #
        case other:
            return BranchResponse(BranchStatus.REQUEST_FAILURE, "Invalid command.")


def handle_command_buildbot(branch_client, branch_request: BranchRequest) -> BranchResponse:
    match branch_request.command:
        
        #
        # Ready signal from buildbot.
        #
        case "SIGREADY":
            job = Manager.get_queue().get_running_job_by_client(branch_client)
            if(not job is None):
                blog.info("Build job '{}' completed.".format(job.get_jobid()))

                if(job.get_status() == "BUILD_FAILED"):
                    job.set_status("FAILED")
                else:
                    stor = packagestorage.storage()
                    
                    blog.info("Hashing package..")
                    md5_hash = hashlib.md5()
                    with open(job.buildbot.file_target, "rb") as hash_file:
                        # read chunk by chunk
                        for chunk in iter(lambda: hash_file.read(4096), b""):
                            md5_hash.update(chunk)

                        blog.info("Deploying package to storage..")
                        shutil.move(job.buildbot.file_target, stor.add_package(job.pkg_payload, md5_hash.hexdigest()))
                        job.set_status("COMPLETED")

                Manager.get_queue().notify_job_completed(job)
 
            # we are done, reset
            branch_client.file_target = None
            branch_client.file_target_bytes = 0          

            branch_client.send_command(BranchResponse(BranchStatus.OK, "Ready signal acknowledged"))
            blog.info("Client {} is ready for commands.".format(branch_client.get_identifier()))

            branch_client.is_ready = True
            Manager.get_scheduler().schedule()

            blog.info("Reevaluating deployment configuration..")
            Manager.determine_deployment_configuration()

        
        #
        # PONG from buildbot
        #
        case "PONG":
            blog.debug("Got PONG from {}.".format(branch_client.get_identifier()))
            branch_client.is_ready = True
            branch_client.alive = True

            # notify queue, because we might have got a job while sending keepalive
            Manager.get_scheduler().schedule()
            return None
        #
        # Get deployment configuration
        #
        case "GETDEPLOYMENTCONFIG":
            return BranchResponse(BranchStatus.OK, Manager.deployment_config)

        #
        # Report status update 
        #
        case "REPORTSTATUSUPDATE":
            if(branch_request.payload == ""):
                return BranchResponse(BranchStatus.REQUEST_FAILURE, "Invalid status update.")

            job = Manager.get_queue().get_running_job_by_client(branch_client)
            if(job is None):
                return BranchResponse(BranchStatus.REQUEST_FAILURE, "No job assigned to client.")

            match branch_request.payload:

                #
                # Initial status update, job accepted by buildbot.
                # Set accepted flag
                #
                case "JOB_ACCEPTED":
                    blog.info("Build job '{}' accepted by {}!".format(job.get_jobid(), branch_client.get_identifier()))
                    
                    # set accepted flag for overwatch
                    job.job_accepted = True
                    job.set_status("JOB_ACCEPTED")
                
                #
                # no special handling required, 
                # informational status update
                #
                case other:
                    blog.info("Build job '{}' on buildbot '{}' status update received: {}".format(job.get_jobid(), branch_client.get_identifier(), branch_request.payload))
                    job.set_status(branch_request.payload)
            
            return BranchResponse(BranchStatus.OK, "Job status updated.")


        #
        # Submit a log for the current job
        #
        case "APPENDLOG":
            job = Manager.get_queue().get_running_job_by_client(branch_client)

            if(not job is None):
                job.append_buildlog(branch_request.payload)
                return BranchResponse(BranchStatus.OK, "Build log update acknowleged.")

            return BranchResponse(BranchStatus.REQUEST_FAILURE, "No job assigned to buildbot.")

        
        #
        # Set the connection to file transfer mode
        #
        case "FILETRANSFERMODE":
            try:
                datalength = int(branch_request.payload)
            except Exception:
                return BranchResponse(BranchStatus.REQUEST_FAILURE, "Datalength is invalid.")

            job = Manager.get_queue().get_running_job_by_client(branch_client)

            if(job is None):
                return BranchResponse(BranchStatus.REQUEST_FAILURE, "No job assigned.")

            job.set_status("UPLOADING")
            branch_client.file_transfer_mode = True
            branch_client.file_target = os.path.join(server.STAGING_AREA, "{}-{}.lfpkg".format(job.pkg_payload.name, job.id))
            branch_client.file_target_bytes = datalength
            return BranchResponse(BranchStatus.OK, "File transfer setup completed.")

        
        #
        # Get extra source information by ID
        #
        case "GETEXTRASOURCEINFO":
            res = extrasourcestorage.storage.get_extra_source_blob_by_id(branch_request.payload)
            
            if(res is None):
                return BranchResponse(BranchStatus.REQUEST_FAILURE, "No such extrasource available.")

            blob = res[0]
            extra_source_info = extrasourcestorage.storage.get_extra_source_info_by_id(branch_request.payload)
            
            data_info = {
                "filename": extra_source_info.filename,
                "datalength": len(blob)
            }
            return BranchResponse(BranchStatus.OK, data_info)

        #
        # Request the actual file
        #
        case "FETCHEXTRASOURCE":
            if(branch_request.payload == ""):
                return BranchResponse(BranchStatus.REQUEST_FAILURE, "Invalid extra source id.")
             
            blob = extrasourcestorage.storage.get_extra_source_blob_by_id(branch_request.payload)[0]
            
            if(blob is None):
                return BranchResponse(BranchStatus.REQUEST_FAILURE, "Invalid extra source id.")

            branch_client.send_data(blob)
            return None
        
        #
        # Set buildbot machine information
        #
        case "SETMACHINEINFO":
            if(branch_request.payload == ""):
                return BranchResponse(BranchStatus.REQUEST_FAILURE, "Invalid machine dictionary.")

            branch_client.set_sysinfo(branch_request.payload)
            return BranchResponse(BranchStatus.OK, "Machine information set")

        #
        # Invalid commands
        #
        case other:
            return BranchResponse(BranchStatus.REQUEST_FAILURE, "Invalid command.")

