import json
import os
import time
import selectors
import shutil
import hashlib
import main
import blog
import uuid
import packagebuild

from config import config
from localstorage import extrasourcestorage
from localstorage import packagestorage 
from localstorage import pkgbuildstorage
from manager import queue
from manager import job
from dependency import dependency
from overwatch import overwatch
from bsocket import server

def handle_command(manager, client, command):
    cmd_header_loc = command.find(" ")
    cmd_header = ""
    cmd_body = ""
    
    # One word command
    if(cmd_header_loc == -1):
        cmd_header = command
    else:
        cmd_header = command[0:cmd_header_loc]
        cmd_body = command[cmd_header_loc+1:len(command)]

    match client.client_type:
        case None:
            return handle_command_untrusted(manager, client, cmd_header, cmd_body)
        
        case "CONTROLLER":
            return handle_command_controller(manager, client, cmd_header, cmd_body)
    
        case "BUILD":
            return handle_command_build(manager, client, cmd_header, cmd_body)
        
        case other:
            return None
  
def handle_command_untrusted(manager, client, cmd_header, cmd_body):
    
    #
    # Match on CMD_HEAD
    #
    match cmd_header:

        #
        # Used by a client to send it's auth key
        # AUTH <KEY>
        #
        case "AUTH":
            # check if trusted mode, or not
            if(config.config.get_config_option("Masterserver")["UntrustedClients"] == "True"):
                return "UNTRUSTED_MODE"
            
            # check if already authenticated
            if(client.is_authenticated):
                return "ALREADY_AUTHENTICATED"
            else:
                blog.debug("Client '{}' authenticating with key: {}".format(client.get_identifier(), cmd_body))

                # fetch auth keys from config
                authkeys_str = config.config.get_config_option("Masterserver")["AuthKeys"]
                authkeys = config.config.parse_str_array(authkeys_str)

                if(cmd_body in authkeys):
                    client.is_authenticated = True
                    blog.info("Client authentication completed.")
                    return "AUTH_OK"
                else:
                    return "INV_AUTH_KEY"
        
        #
        # Used by a client to set it's machine type
        # SET_MACHINE_TYPE <TYPE>
        # (controller, build)
        #
        case "SET_MACHINE_TYPE":

            # Check if the server allows untrusted clients
            # or the client is authenticated
            if(client.is_authenticated or (config.config.get_config_option("Masterserver")["UntrustedClients"] == "True")):
                
                # match cmd_body
                match cmd_body:
                    # CONTROLLER client assigment
                    case "CONTROLLER":
                        blog.info("Machine type assigned. Client '{}' is authenticated as controller client type.".format(client.get_identifier()))
                        client.client_type = "CONTROLLER"
                        return "CMD_OK"

                    # BUILD client assignment
                    case "BUILD":
                        blog.info("Machine type assigned. Client '{}' is authenticated as build client type.".format(client.get_identifier()))
                        client.client_type = "BUILD"
                        blog.debug("Launching overwatch thread for new client..")
                        overwatch.check_buildbot_alive(client)
                        blog.debug("Overwatch ready.")
                        return "CMD_OK"
                    
                    # INV Machine type
                    case other:
                        return "INV_MACHINE_TYPE"
            else:
                return "AUTH_REQUIRED"
        
        #
        # Handle INV_CMD
        #
        case other:
            blog.debug("Received a malformed command from client {}".format(client.client_uuid))
            return "INV_CMD"

def handle_command_controller(manager, client, cmd_header, cmd_body):
    
    #
    # Match on CMD_HEAD
    #
    match cmd_header:
        #
        # Used by a client to set it's display name
        # SET_MACHINE_NAME <NAME>
        #
        case "SET_MACHINE_NAME":
            blog.info("Client name changed. Client '{}' is now known as '{}'".format(client.get_identifier(), cmd_body))
            client.set_identifier(cmd_body)
            return "CMD_OK"
        
        #
        # checkout a package build file
        # CHECKUT_PACKAGE <NAME>
        #  
        case "CHECKOUT_PACKAGE":
            pkg_build = pkgbuildstorage.storage.get_packagebuild_obj(cmd_body)
            
            if(pkg_build is None):
                return "INV_PKG_NAME"
            else:
                blog.info("Client {} checked out package '{}'!".format(client.get_identifier(), cmd_body))
                return pkg_build.get_json()

        #
        # submit a package build file
        # SUBMIT_PACKAGE <PAYLOAD>
        #
        case "SUBMIT_PACKAGE":
            if(len(cmd_body) == 0):
                return "INV_PKG_BUILD"

            pkgbuild = packagebuild.package_build.from_json(cmd_body)
            if(not pkgbuild.is_valid()):
                return "INV_PKG_BUILD"
            
            if(not pkgbuildstorage.storage.add_packagebuild_obj(pkgbuild)):
                return "INV_PKG_BUILD"

            return "CMD_OK"
     
        #
        # Controller client requested clean release build
        # RELEASE_BUILD <NAME>
        #
        case "RELEASE_BUILD":
            if(not manager.deployment_config["deploy_realroot"]):
                return "RELEASE_ENV_UNAVAILABLE"

            if(len(cmd_body) == 0):
                return "INV_PKG_NAME"

            pkgbuild = pkgbuildstorage.storage.get_packagebuild_obj(cmd_body)
            
            if(pkgbuild is None):
                return "INV_PKG_NAME"

            # get a job obj, crosstools = False
            job = manager.new_job(False)

            job.pkg_payload = pkgbuild
            job.requesting_client = client.get_identifier()
            job.set_status("WAITING")

            res = manager.get_queue().add_to_queue(job)
            manager.get_queue().update()
            return res


        #
        # Controller client requested clean cross build
        # CROSS_BUILD <NAME>
        #
        case "CROSS_BUILD":
            if(not manager.deployment_config["deploy_crossroot"]):
                return "CROSS_ENV_UNAVAILABLE"

            if(len(cmd_body) == 0):
                return "INV_PKG_NAME"

            pkgbuild = pkgbuildstorage.storage.get_packagebuild_obj(cmd_body)
            
            if(pkgbuild is None):
                return "INV_PKG_NAME"

            # get a job obj, crosstools = False
            job = manager.new_job(False)

            job.pkg_payload = pkgbuild
            job.requesting_client = client.get_identifier()
            job.set_status("WAITING")

            res = manager.get_queue().add_to_queue(job)
            manager.get_queue().update()
            return res
      
        #
        # Requests log for a package build
        # VIEW_LOG <JOB_ID>
        #
        case "VIEW_LOG":
            if(cmd_body == ""):
                return "INV_JOB_ID"
            
            job = manager.get_job_by_id(cmd_body)
            
            if(job is None):
                return "INV_JOB_ID"
            
            if(job.build_log is None):
                return "NO_LOG"

            return json.dumps(job.build_log)
        
        #
        # Requests system events from Masterserver
        # VIEW_SYS_EVENTS
        #
        case "VIEW_SYS_EVENTS":
            return json.dumps(manager.system_events)
    
        #
        # get dependenders for a given package
        # GET_DEPENDERS <NAME>
        #
        case "GET_DEPENDERS":
            names = pkgbuildstorage.storage.get_all_packagebuild_names()
            pkgs = pkgbuildstorage.storage.get_all_packagebuilds()

            if(cmd_body in names):
                release_build, cross_build = dependency.find_dependers(pkgs, cmd_body, set())
                
                all_dependers = {
                    "releasebuild": release_build,
                    "crossbuild": cross_build
                }

                return json.dumps(all_dependers)

            else:
                return "INV_PKG_NAME"
        

        #
        # Rebuild all packages that depenend on the specified
        # package.
        #
        case "REBUILD_DEPENDERS":
            # Both environments need to be available
            if(not manager.deployment_config["deploy_realroot"]):
                return "RELEASE_ENV_UNAVAILABLE"

            if(not manager.deployment_config["deploy_crossroot"]):
                return "CROSS_ENV_UNAVAILABLE"

            names = pkgbuildstorage.storage.get_all_packagebuild_names()
            pkgs = pkgbuildstorage.storage.get_all_packagebuilds()

            if(not cmd_body in names):
                return "INV_PKG_NAME"
            
            release_build, cross_build = dependency.find_dependers(pkgs, cmd_body, set())

            # start node
            start_pkgbuild = pkgbuildstorage.storage.get_packagebuild_obj(cmd_body)
            if(start_pkgbuild.cross_dependencies == [ ]):
                release_build.append(start_pkgbuild.name)
            else:
                cross_build.append(start_pkgbuild.name)


            for dep in release_build:
                pkgbuild = pkgbuildstorage.storage.get_packagebuild_obj(dep)
                blog.info("Creating releasebuild job for {}".format(pkgbuild.name))
                
                # get a job obj, crosstools = False
                job = manager.new_job(False)

                job.pkg_payload = pkgbuild
                job.requesting_client = client.get_identifier()
                job.set_status("WAITING")

                manager.add_job_to_queue(job)
                blog.info("Adding to queue")
            
            for dep in cross_build:
                pkgbuild = pkgbuildstorage.storage.get_packagebuild_obj(dep)
                blog.info("Creating crossbuild job for {}".format(pkgbuild.name))
                
                # get a job obj, crosstools = True
                job = manager.new_job(True)

                job.pkg_payload = pkgbuild
                job.requesting_client = client.get_identifier()
                job.set_status("WAITING")

                manager.add_job_to_queue(job)
            
            manager.get_queue().update()
            return "CMD_OK"



        #
        # Get all completed build jobs 
        # COMPLETED_JOBS_STATUS
        #
        case "COMPLETED_JOBS_STATUS":
            completed_jobs = manager.get_completed_jobs()
            return json.dumps([obj.get_info_dict() for obj in completed_jobs])
 
        #
        # Get all currently running build jobs 
        # RUNNING_JOBS_STATUS
        #
        case "RUNNING_JOBS_STATUS":
            running_jobs = manager.get_running_jobs()
            return json.dumps([obj.get_info_dict() for obj in running_jobs])

        #
        # Get queued jobs 
        # QUEUED_JOBS_STATUS
        #
        case "QUEUED_JOBS_STATUS":
            queued_jobs = manager.get_queued_jobs()
            return json.dumps([obj.get_info_dict() for obj in queued_jobs])

        #
        # Get connected controller type clients
        # CONNECTED_CONTROLLERS
        #
        case "CONNECTED_CONTROLLERS":
            clients = manager.get_controller_names()
            return json.dumps(clients)

        #
        # Get connected build type clients
        # CONNECTED_BUILDBOTS
        #
        case "CONNECTED_BUILDBOTS":
            buildbots = manager.get_buildbot_names()
            return json.dumps(buildbots)

        #
        # Get a list of all managed packages
        # MANAGED_PACKAGES
        #
        case "MANAGED_PACKAGES":
            stor = packagestorage.storage()
            return json.dumps(stor.packages)
            
        #
        # Get a list of all managed packagebuilds
        # MANAGED_PKGBUILDS
        #
        case "MANAGED_PKGBUILDS":
            return json.dumps(pkgbuildstorage.storage.get_all_packagebuild_names())

        #
        # Clear completed jobs
        # CLEAR_COMPLETED_JOBS
        #
        case "CLEAR_COMPLETED_JOBS":
            manager.clear_completed_jobs()  
            return "JOBS_CLEARED"
    
        #
        # Cancel queued jobs
        # CANCEL_QUEUED_JOB <ID>
        #
        case "CANCEL_QUEUED_JOB":
            if(cmd_body == ""):
                return "INV_JOB_ID"
            
            job = manager.get_job_by_id(cmd_body)
            
            if(job is None):
                return "INV_JOB_ID"
           
            manager.cancel_queued_job(job) 
            return "JOB_CANCELED"

        #
        # Cancel all queued jobs
        # CANCEL_ALL_QUEUED_JOBS
        #
        case "CANCEL_ALL_QUEUED_JOBS":
            manager.cancel_all_queued_jobs()
            return "JOBS_CANCELED"
   
        #
        # Releasebuild a solution
        # SUBMIT_SOLUTION_RB <SOL>
        #
        case "SUBMIT_SOLUTION_RB":
            if(not manager.deployment_config["deploy_realroot"]):
                return "RELEASE_ENV_UNAVAILABLE"

            if(cmd_body == ""):
                return "INV_SOL"
            
            solution = json.loads(cmd_body)
            jobs, status = dependency.job_arr_from_solution(manager, client, solution, False)
           
            if(jobs is None):
                return "PKG_BUILD_MISSING {}".format(status)

            for job in jobs:
                manager.add_job_to_queue(job)

            # queue every job
            for job in jobs:
                manager.get_queue().add_to_queue(job)
                manager.get_queue().update()

            return "BATCH_QUEUED"
       
        #
        # Releasebuild a solution
        # SUBMIT_SOLUTION_CB <SOL>
        #
        case "SUBMIT_SOLUTION_CB":
            if(not manager.deployment_config["deploy_crossroot"]):
                return "CROSS_ENV_UNAVAILABLE"

            if(cmd_body == ""):
                return "INV_SOL"
            
            solution = json.loads(cmd_body)
            jobs, status = dependency.job_arr_from_solution(manager, client, solution, True)
           
            if(jobs is None):
                return "PKG_BUILD_MISSING {}".format(status)

            for job in jobs:
                manager.add_job_to_queue(job)

            # queue every job
            for job in jobs:
                manager.get_queue().add_to_queue(job)
                manager.get_queue().update()

            return "BATCH_QUEUED"
        
        #
        # Get various client information
        #
        case "GET_CLIENT_INFO":
            if(cmd_body == ""):
                return "INV_CLIENT_NAME"

            target_client = manager.get_client_by_name(cmd_body)
            if(target_client == None):
                return "INV_CLIENT_NAME"

            return json.dumps(target_client.get_sysinfo())

        #
        # Get locked packages (currently being downloaded)
        #
        case "GET_LOCKED_PACKAGES":
            names = [ ]

            for pkg in packagestorage.storage.locked_files:
                if(not pkg.pkg_name in names):
                    names.append(pkg.pkg_name)

            return json.dumps(names)
        
        #
        # Request a package / pkgbuild deletion.
        #
        case "DELETE_PKGBUILD":
            if(cmd_body == ""):
                return "INV_CMD"

            if(not cmd_body in pkgbuildstorage.storage.get_all_packagebuild_names()):
                return "INV_PKG_NAME"
            
            # cant delete crosstools if they are enabled
            if(cmd_body == "crosstools"):
                if(manager.deployment_config["deploy_crossroot"]):
                    return "REQUIRED_PKG"
            
            # cant delete realroot packages if they are enabled.
            if(cmd_body in manager.deployment_config["realroot_packages"]):
                if(manager.deployment_config["deploy_realroot"]):
                    return "REQUIRED_PKG"

            blog.debug("Deleting packagebuild..")
            pkgbuildstorage.storage.remove_packagebuild(cmd_body)

            blog.debug("Deleting package..")
            
            # not locked, can delete
            if(not packagestorage.storage.check_package_lock(cmd_body)):
                packagestorage.storage().remove_package(cmd_body)
            else:
                blog.warn("Package requested for deletion is currently locked, added to deletion queue.")
                packagestorage.storage.deletion_queue.append(cmd_body)

            return "CMD_OK"

        #
        # Receive extra sources from client
        #
        # TRANSFER_EXTRA_SOURCE BYTES DESCRIPTION FILENAME
        case "TRANSFER_EXTRA_SOURCE":
            file_info = json.loads(cmd_body)
            byte_count = 0

            try:
                byte_count = int(file_info["filelen"])
            except Exception:
                return "BYTE_COUNT_ERR"
            
            _id = uuid.uuid4()
            desc = file_info["description"]
            file_name = file_info["filename"]

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
            return "CMD_OK"
        
        #
        # Called when a client completes an extra source upload
        # adds the specified extra source to the database
        #
        case "COMPLETE_TRANSFER":
            pending_extra_src = None

            # find correct pending job
            for pes in manager.get_pending_extra_sources():
                if(pes.client.client_uuid == client.client_uuid):
                    pending_extra_src = pes
                    break
            
            target_file = os.path.join(server.STAGING_AREA, "{}.es".format(pending_extra_src.id))
            
            _bytes = [ ]

            with open(target_file, "rb") as _file:
                _bytes = _file.read()

            if(not extrasourcestorage.storage.add_extrasource(str(pending_extra_src.id), pending_extra_src.file_name, pending_extra_src.desc, _bytes)):
                return "ERR_COULD_NOT_INSERT"
            
            # remove pending extra src
            manager.remove_pending_extra_source(pending_extra_src)
            
            # delete staged extra sourcefile
            blog.info("Removing temporary file in staging directory..")
            try:
                os.remove(target_file)
            except Exception as ex:
                blog.warn("Could not delete temporary file: {}".format(ex))

            return "CMD_OK"

        #
        # Get all managed extra sources
        #
        case "GET_MANAGED_EXTRA_SOURCES":
            return json.dumps([obj.get_json() for obj in extrasourcestorage.storage.get_all_extrasources()])

        #   
        # Deletes an extra source by id
        #
        case "REMOVE_EXTRA_SOURCE":
            if(cmd_body == "" or cmd_body is None):
                return "INV_ES_ID"
                
            if(extrasourcestorage.storage.remove_extrasource_by_id(cmd_body)):
                return "CMD_OK"
            else:
                return "INV_ES_ID"

        #
        # Invalid command
        #
        case other:
            blog.debug("Received a malformed command from client {}".format(client.client_uuid))
            return "INV_CMD"



def handle_command_build(manager, client, cmd_header, cmd_body):
    
    #
    # Match on CMD_HEAD
    #
    match cmd_header:
        #
        # Used by a client to set it's display name
        # SET_MACHINE_NAME <NAME>
        #
        case "SET_MACHINE_NAME":
            blog.info("Client name changed. Client '{}' is now known as '{}'".format(client.get_identifier(), cmd_body))
            client.client_name = cmd_body
            return "CMD_OK"

        #
        # Buildbot reported system information
        # CPU, RAM, free disk space, hostname
        #
        case "SET_MACHINE_INFORMATION":
            if(cmd_body == ""):
                return "INV_CMD"

            client.set_sysinfo(json.loads(cmd_body))
            return "CMD_OK"

        # 
        # Build client sends ready signal
        # SIG_READY
        #
        case "SIG_READY":
            # check if client just finished a job or not
            job = manager.get_job_by_client(client)
            if(not job is None):
                blog.info("Build job '{}' completed.".format(job.get_jobid()))

                if(job.get_status() == "BUILD_FAILED"):
                    job.set_status("FAILED")
                else:
                    stor = packagestorage.storage()
                    
                    blog.info("Hashing package..")
                    md5_hash = hashlib.md5()
                    hash_file = open(job.client.file_target, "rb")

                    # read chunk by chunk
                    for chunk in iter(lambda: hash_file.read(4096), b""):
                        md5_hash.update(chunk)

                    blog.info("Deploying package to storage..")
                    shutil.move(job.client.file_target, stor.add_package(job.pkg_payload, md5_hash.hexdigest()))
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
            return None
        
        #
        # PONG from buildbot!
        # PONG
        #
        case "PONG":
            blog.debug("Got PONG from {}.".format(client.get_identifier()))
            client.is_ready = True
            client.alive = True

            # notify queue, because we might have got a job while sending keepalive
            manager.queue.update()
            return "CMD_ACK"

        
 
        #
        # Fetch deployment configuration from the server
        #
        case "GET_DEPLOYMENT_CONFIG":
            res = manager.deployment_config 
            return json.dumps(res)

    
        #
        # Receive a status update from the buildbot
        #
        case "REPORT_STATUS_UPDATE":
            if(cmd_body == ""):
                return "INV_CMD"
            
            job = manager.get_job_by_client(client)
            
            if(job is None):
                return "NO_JOB"

            match cmd_body:

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

            
            return "STATUS_ACK"

        #
        # Receive log from buildbot
        # SUBMIT_LOG <LOG>
        #
        case "SUBMIT_LOG":
            job = manager.get_job_by_client(client)

            if(not job is None):
                blog.info("Build job '{}' log received.".format(job.get_jobid()))
                job.set_buildlog(json.loads(cmd_body))
                job.job_accepted = True
                return "LOG_OK"

            return "NO_JOB"

        #
        # Switch connection to FILE_TRANSFER_MODE
        # FILE_TRANSFER_MODE <BYTES>
        #
        case "FILE_TRANSFER_MODE":
            byte_count = 0

            try:
                byte_count = int(cmd_body)
            except Exception:
                return "BYTE_COUNT_ERR"

            job = manager.get_job_by_client(client)

            if(not job is None):
                job.set_status("UPLOADING")

                client.file_transfer_mode = True
                client.file_target = os.path.join(server.STAGING_AREA, "{}-{}.lfpkg".format(job.pkg_payload.name, job.job_id))
                client.file_target_bytes = byte_count
                return "ACK_FILE_TRANSFER"
            else:
                return "NO_JOB"
        
        #
        # Report system event to masterserver
        # REPORT_SYS_EVENTS <SYSEVT>
        #
        case "REPORT_SYS_EVENTS":
            if(cmd_body is None):
                return "EMPTY_SYS_EVENT"

            blog.info("Received System Event report from {}.".format(client.get_identifier()))
            manager.report_system_event(client.get_identifier(), cmd_body)
            return "RECV_SYS_EVENT"
    
        #
        # Checkout extra source information from
        # masterserver.
        #
        case "EXTRA_SOURCE_INFO":
            if(cmd_body == ""):
                return "INV_EXTRA_SOURCE"
            

            # TODO: check if SQLite has a function for this which would probably be more efficient..
            res = extrasourcestorage.storage.get_extra_source_blob_by_id(cmd_body)

            if(res is None):
                return "INV_EXTRA_SOURCE"

            blob = res[0]
            extra_source_info = extrasourcestorage.storage.get_extra_source_info_by_id(cmd_body)
            
            data_info = {
                "filename": extra_source_info.filename,
                "datalen": len(blob)
            }

            return json.dumps(data_info)
        
        #
        # Fetch extra source blob 
        # Returns blob (if available) on request
        #
        case "FETCH_EXTRA_SOURCE":
            if(cmd_body == ""):
                return "INV_EXTRA_SOURCE"
            
            blob = extrasourcestorage.storage.get_extra_source_blob_by_id(cmd_body)[0]
            
            if(blob is None):
                return "INV_EXTRA_SOURCE"

            client.send_data(blob)
            return None


        #
        # Invalid command
        #
        case other:
            blog.debug("Received a malformed command from client {}".format(client.client_uuid))
            return "INV_CMD"
