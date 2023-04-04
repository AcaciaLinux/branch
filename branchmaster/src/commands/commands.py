import main
import blog
import packagebuild

from branchpacket import BranchRequest, BranchResponse, BranchStatus
from manager.manager import manager
from localstorage import extrasourcestorage
from dependency import dependency
from localstorage import packagestorage 
from localstorage import pkgbuildstorage

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
            
            # unpack payload
            machine_identifier: str = branch_request.payload["machine_identifier"]
            machine_type: str = branch_request.payload["machine_type"]
            machine_authkey: str = branch_request.payload["machine_authkey"]
            machine_version: int = branch_request.payload["machine_version"]
            
            # Check if protocol version matches
            if(main.BRANCH_PROTOCOL_VERSION != machine_version):
                return BranchResponse(BranchStatus.REQUEST_FAILURE, "Protocol version is not matching. Requested protocol {}, while the server only provides protocol {}.".format(main.BRANCH_PROTOCOL_VERSION, machine_version))
            
            # Check if authkey is valid
            if(manager.is_authkey_valid(machine_authkey)):
                blog.info("Client authentication completed for '{}'.".format(branch_client.get_identifier()))
            else:
                blog.warn("Client authentication failed for '{}'.".format(branch_client.get_identifier()))
                return BranchResponse(BranchStatus.REQUEST_FAILURE, "Authkey is invalid.")
            
            # Check if identifier is valid
            if(branch_client.set_identifier(machine_identifier)):
                blog.info("Client with UUID '{}' is now known as '{}'.".format(branch_client.client_uuid, branch_client.get_identifier())) 
            else:
                return BranchResponse(BranchStatus.REQUEST_FAILURE, "Requested client name is not permitted.")

            # Check if machine type is valid
            if(branch_client.set_type(machine_type)):
                blog.info("Client type '{}' assigned to '{}'.".format(machine_type, branch_client.get_identifier()))
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

            job = manager.new_job(branch_request.payload["buildtype"] == "CROSS", pkgbuild, branch_client.get_identifier())
            res = manager.get_queue().add_to_queue(job)
            manager.get_queue().update()

            # 0 -> BUILD QUEUED
            if(res == 0):
                return BranchResponse(BranchStatus.OK, "Build request added to queue.")
            # 1 -> BUILD SUBMITTED
            elif(res == 1):
                return BranchResponse(BranchStatus.OK, "Build request immediately handled.")
        
        #
        # Get job log
        #
        case "GETJOBLOG":
            job = manager.get_job_by_id(branch_request.payload)
            
            if(job is None):
                return BranchResponse(BranchStatus.REQUEST_FAILURE, "No such job is available.")
            
            build_log = job.get_buildlog()
            if(build_log is None):
                return BranchResponse(BranchStatus.REQUEST_FAILURE, "No job log available.")

            return BranchResponse(BranchStatus.OK, build_log)
        
        #
        # Get syslog
        #
        case "GETSYSLOG":
            return BranchResponse(BranchStatus.OK, manager.system_events)

        #
        # Get dependers
        #
        case "GETDEPENDERS":
            names = pkgbuildstorage.storage.get_all_packagebuild_names()
            pkgbuilds = pkgbuildstorage.storage.get_all_packagebuilds()
            
            if(not branch_request.payload in names):
                return BranchResponse(BranchStatus.REQUEST_FAILURE, "Specified packagebuild does not exist.")

            release_build, cross_build = dependency.find_dependers(pkgbuilds, branch_request.payload, set())
            
            all_dependers = {
                "releasebuild": release_build,
                "crossbuild": cross_build
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

            release_build, cross_build = dependency.find_dependers(pkgbuilds, branch_request.payload, set())
            
            # start node
            start_pkgbuild = pkgbuildstorage.storage.get_packagebuild_obj(branch_request.payload)
            if(start_pkgbuild.cross_dependencies == [ ]):
                release_build.append(start_pkgbuild.name)
            else:
                cross_build.append(start_pkgbuild.name)

            for dep in release_build:
                pkgbuild = pkgbuildstorage.storage.get_packagebuild_obj(dep)
                blog.info("Creating releasebuild job for {}".format(pkgbuild.name))
                
                # get a job obj, crosstools = False
                job = manager.new_job(False, pkgbuild, branch_client.get_identifier())
            
            for dep in cross_build:
                pkgbuild = pkgbuildstorage.storage.get_packagebuild_obj(dep)
                blog.info("Creating crossbuild job for {}".format(pkgbuild.name))
                
                # get a job obj, crosstools = True
                job = manager.new_job(True, pkgbuild, branch_client.get_identifier())
            
            manager.get_queue().update()
            return BranchResponse(BranchStatus.OK, "Rebuild dependers requested.")

        
        #
        # Get job status
        #
        case "GETJOBSTATUS":
            queued_jobs = manager.get_queued_jobs()
            running_jobs = manager.get_running_jobs()
            completed_jobs = manager.get_completed_jobs()
            
            return BranchResponse(BranchStatus.OK, {
                "queuedjobs": [obj.get_info_dict() for obj in queued_jobs],
                "runningjobs": [obj.get_info_dict() for obj in running_jobs],
                "completedjobs": [obj.get_info_dict() for obj in completed_jobs]
            })

        #
        # Get connected clients
        #
        case "GETCONNECTEDCLIENTS":
            controllers = manager.get_controller_names()
            buildbots = manager.get_buildbot_names()
        
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
            manager.clear_completed_jobs()  
            return BranchResponse(BranchStatus.OK, "Completed jobs cleared.")
        
        #
        # Cancel all queued jobs
        #
        case "CANCELQUEUEDJOBS":
            manager.cancel_all_queued_jobs()
            return BranchResponse(BranchStatus.OK, "All queued jobs canceled.")
        
        #
        # Cancel a queued job by id
        #
        case "CANCELQUEUEDJOB":
            job = manager.get_job_by_id(branch_request.payload)
            
            if(job == None):
                return BranchResponse(BranchStatus.REQUEST_FAILURE, "No such job found")
           
            if(manager.cancel_queued_job(job)):
                return BranchResponse(BranchStatus.OK, "Job canceled successfully.")
            else:
                return BranchResponse(BranchStatus.REQUEST_FAILURE, "Specified job is not queued.")

        #
        # Submit a solution for building
        #
        case "SUBMITSOLUTION":
            if(not "solution" in branch_request.payload):
                return BranchResponse(BranchStatus.REQUEST_FAILURE, "Missing request data: solution")

            if(not "buildtype" in branch_request.payload):
                return BranchResponse(BranchStatus.REQUEST_FAILURE, "Missing request data: buildtype")
            
            if(branch_request.payload["buildtype"] == "RELEASE" and not manager.deployment_config["deploy_realroot"]):
                return BranchResponse(BranchStatus.REQUEST_FAILURE, "Release build environment is disabled or unavailable.")
 
            if(branch_request.payload["buildtype"] == "CROSS" and not manager.deployment_config["deploy_crossroot"]):
                return BranchResponse(BranchStatus.REQUEST_FAILURE, "Cross build environment is disabled or unavailable.")


            if(branch_request.payload["solution"] == ""):
                return BranchResponse(BranchStatus.REQUEST_FAILURE, "Invalid solution.")
            
            jobs, status = dependency.job_arr_from_solution(branch_client, branch_request.payload["solution"], "CROSS" == branch_request.payload["buildtype"])
           
            if(jobs is None):
                return BranchResponse(BranchStatus.REQUEST_FAILURE, "Required package build '{}' is missing.".format(status))

            for job in jobs:
                manager.add_job_to_queue(job)

            # queue every job
            for job in jobs:
                manager.get_queue().add_to_queue(job)
                manager.get_queue().update()

            return BranchResponse(BranchStatus.OK, "Solution queued.")
        
        #
        # Get all available client info
        #
        case "GETCLIENTINFO":
            target_client = manager.get_client_by_name(branch_request.payload)
            if(target_client == None):
                return BranchResponse(BranchStatus.REQUEST_FAILURE, "No such client found.")

            return BranchResponse(BranchStatus.OK, target_client.get_sysinfo())
        
        #
        # Delete a package and packagebuild.
        #
        case "DELETEPKG":
            if(not branch_request.payload in pkgbuildstorage.storage.get_all_packagebuild_names()):
                return BranchResponse(BranchStatus.REQUEST_FAILURE, "No such packagebuild.")
            
            # cant delete crosstools if they are enabled
            if(cmd_body == "crosstools"):
                if(manager.deployment_config["deploy_crossroot"]):
                    return BranchResponse(BranchStatus.REQUEST_FAILURE, "The requested package is enabled in the current deployment configuration. Cannot delete.")
            
            # cant delete realroot packages if they are enabled.
            if(cmd_body in manager.deployment_config["realroot_packages"]):
                if(manager.deployment_config["deploy_realroot"]):
                    return BranchResponse(BranchStatus.REQUEST_FAILURE, "The requested package is enabled in the current deployment configuration. Cannot delete.")

            blog.debug("Deleting packagebuild..")
            pkgbuildstorage.storage.remove_packagebuild(branch_request.payload)

            blog.debug("Deleting package..")
            
            # not locked, can delete
            if(not packagestorage.storage.check_package_lock(cmd_body)):
                packagestorage.storage().remove_package(cmd_body)
            else:
                blog.warn("Package requested for deletion is currently locked, added to deletion queue.")
                packagestorage.storage.deletion_queue.append(cmd_body)

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
            else:
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

            file_info = json.loads(cmd_body)
            byte_count = 0

            try:
                byte_count = int(file_info["filelen"])
            except Exception:
                return BranchResponse(BranchStatus.REQUEST_FAILURE, "'filelength' needs to be a valid integer.")
            
            _id = uuid.uuid4()
            desc = branch_request.payload["description"]
            file_name = branch_request.payload["filename"]

            #
            # Extra Source pending class
            #
            class extra_source_pending():
                def __init__(self, client, _id, file_name, desc):
                    self.client = client
                    self.id = _id
                    self.desc = desc
                    self.file_name = file_name

            manager.add_pending_extra_source(extra_source_pending(client, _id, file_name, desc))

            client.file_target = os.path.join(server.STAGING_AREA, "{}.es".format(_id))
            client.file_target_bytes = byte_count
            client.file_transfer_mode = True
            return BranchResponse(BranchStatus.OK, "Transfer setup.")
        
        #
        # Complete extra source transfer, commit package to database
        #
        case "COMPLETETRANSFER":
            pending_extra_src = None

            # find correct pending job
            for pes in manager.get_pending_extra_sources():
                if(pes.client.client_uuid == client.client_uuid):
                    pending_extra_src = pes
                    break
            
            target_file = os.path.join(server.STAGING_AREA, "{}.es".format(pending_extra_src.id))
            
            with open(target_file, "rb") as _file:
                _bytes = _file.read()

            if(not extrasourcestorage.storage.add_extrasource(str(pending_extra_src.id), pending_extra_src.file_name, pending_extra_src.desc, _bytes)):
                return BranchResponse(BranchStatus.REQUEST_FAILURE, "Could not insert to database.")
            
            # remove pending extra src
            manager.remove_pending_extra_source(pending_extra_src)
            
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
            job = manager.get_job_by_client(client)
            if(not job is None):
                blog.info("Build job '{}' completed.".format(job.get_jobid()))

                if(job.get_status() == "BUILD_FAILED"):
                    job.set_status("FAILED")
                else:
                    stor = packagestorage.storage()
                    
                    blog.info("Hashing package..")
                    md5_hash = hashlib.md5()
                    hash_file = open(job.buildbot.file_target, "rb")

                    # read chunk by chunk
                    for chunk in iter(lambda: hash_file.read(4096), b""):
                        md5_hash.update(chunk)

                    blog.info("Deploying package to storage..")
                    shutil.move(job.buildbot.file_target, stor.add_package(job.pkg_payload, md5_hash.hexdigest()))
                    job.set_status("COMPLETED")

                manager.move_inactive_job(job)
 
            # we are done, reset
            client.file_target = None
            client.file_target_bytes = 0          

            client.send_command("CMD_OK")
            blog.info("Client {} is ready for commands.".format(client.get_identifier()))

            client.is_ready = True
            manager.queue.update()
            blog.info("Reevaluating deployment configuration..")
            manager.determine_deployment_configuration()
            return BranchResponse(BranchStatus.OK, "Ready signal acknowledged.")

    
    #
    # PONG from buildbot
    #
    case "PONG":
        blog.debug("Got PONG from {}.".format(client.get_identifier()))
        client.is_ready = True
        client.alive = True

        # notify queue, because we might have got a job while sending keepalive
        manager.queue.update()

        return BranchResponse(BranchStatus.OK, "Pong acknowledged.")

    #
    # Get deployment configuration
    #
    case "GETDEPLOYMENTCONFIG":
        return BranchResponse(BranchStatus.OK, manager.deployment_config)

    #
    # Report status update 
    #
    case "REPORTSTATUSUPDATE":
        if(branch_request.payload == ""):
            return BranchResponse(BranchStatus.REQUEST_FAILURE, "Invalid status update.")

        job = manager.get_job_by_client(branch_client)
        if(job is None):
            return "NO_JOB"

        match branch_request.payload:

            #
            # Initial status update, job accepted by buildbot.
            # Set accepted flag
            #
            case "JOB_ACCEPTED":
                blog.info("Build job '{}' accepted by {}!".format(job.get_jobid(), client.get_identifier()))
                
                # set accepted flag for overwatch
                job.job_accepted = True

                job.set_status("JOB_ACCEPTED")
            
            #
            # no special handling required, 
            # informational status update
            #
            case other:
                blog.info("Build job '{}' on buildbot '{}' status update received: {}".format(job.get_jobid(), client.get_identifier(), cmd_body))
                job.set_status(cmd_body)
    
    #
    # Submit a log for the current job
    #
    case "SUBMITLOG":
        job = manager.get_job_by_client(client)

        if(not job is None):
            blog.info("Build job '{}' log received.".format(job.get_jobid()))
            job.set_buildlog(branch_request.payload)
            return BranchResponse(BranchStatus.OK, "Build log accepted.")

        return BranchResponse(BranchStatus.REQUEST_FAILURE, "No job assigned to buildbot.")

    
    #
    # Set the connection to file transfer mode
    #
    case "FILETRANSFERMODE":
        try:
            datalength = int(branch_request.payload)
        except Exception:
            return BranchResponse(BranchStatus.REQUEST_FAILURE, "Datalength is invalid.")

        job = manager.get_job_by_client(client)

        if(job is None):
            return BranchResponse(BranchStatus.REQUEST_FAILURE, "No job assigned.")

        job.set_status("UPLOADING")
        client.file_transfer_mode = True
        client.file_target = os.path.join(server.STAGING_AREA, "{}-{}.lfpkg".format(job.pkg_payload.name, job.job_id))
        client.file_target_bytes = byte_count
        return BranchResponse(BranchStatus.OK, "File transfer setup completed.")

    
    #
    # Request the actual file
    #
    case "FETCHEXTRASOURCE":
        if(branch_request.payload == ""):
            return BranchResponse(BranchStatus.REQUEST_FAILURE, "Invalid extra source id.")
         
        blob = extrasourcestorage.storage.get_extra_source_blob_by_id(cmd_body)[0]
        
        if(blob is None):
            return BranchResponse(BranchStatus.REQUEST_FAILURE, "Invalid extra source id.")

        client.send_data(blob)
        return None
        
    #
    # Invalid commands
    #
    case other:
        return BranchResponse(BranchStatus.REQUEST_FAILURE, "Invalid command.")

