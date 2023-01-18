import json
import os
import time
import selectors
import shutil
import hashlib
import main
import blog
import packagebuild

from config import config
from localstorage import packagestorage 
from localstorage import pkgbuildstorage
from manager import queue
from manager import jobs
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
            client.client_name = cmd_body
            return "CMD_OK"
        
        #
        # checkout a package build file
        # CHECKUT_PACKAGE <NAME>
        #  
        case "CHECKOUT_PACKAGE":
            storage = pkgbuildstorage.storage()

            if(cmd_body in storage.packages):
                blog.info("Client {} checked out package '{}'!".format(client.get_identifier(), cmd_body))
                
                pkg_build = storage.get_json_bpb(cmd_body)
                if(pkg_build is None):
                    return "INV_PKG"
                else:
                    return pkg_build
            else:
                return "INV_PKG_NAME"

        #
        # submit a package build file
        # SUBMIT_PACKAGE <PAYLOAD>
        #
        case "SUBMIT_PACKAGE":
            storage = pkgbuildstorage.storage()

            json_bpb = None
            try:
                json_bpb = json.loads(cmd_body)
            except Exception:
                pass

            if(json_bpb is None):
                return "INV_PKG_BUILD"

            pkgbuild = packagebuild.package_build.from_json(json_bpb)
             
            if(bpb.validate_pkgbuild()):
                return "INV_PKG_BUILD"
            
            tdir = storage.create_stor_directory(pkgbuild.name)

            bpb_file = os.path.join(tdir, "package.bpb")
            if(os.path.exists(bpb_file)):
                os.remove(bpb_file)
           
            pkgbuild.write_build_file(bpb_file)
            return "CMD_OK"
     
        #
        # Controller client requested clean release build
        # RELEASE_BUILD <NAME>
        #
        case "RELEASE_BUILD":
            storage = pkgbuildstorage.storage()
            if(cmd_body in storage.packages):
                blog.info("Controller client requested release build for {}".format(cmd_body))
                
                pkg = storage.get_bpb_obj(cmd_body)

                if(pkg is None):
                    return "PKG_BUILD_DAMAGED"

                # get a job obj, crosstools = False
                job = manager.new_job(False)

                # TODO: remove seperate build_pkg_name, because pkg contains it.
                job.build_pkg_name = pkg.name
                job.pkg_payload = pkg
                job.requesting_client = client.get_identifier()
                job.set_status("WAITING")

                res = manager.get_queue().add_to_queue(job)
                return res
            else:
                blog.info("Controller client requested release build for invalid package.")
                return "INV_PKG_NAME"



        #
        # Controller client requested clean cross build
        # CROSS_BUILD <NAME>
        #
        case "CROSS_BUILD":
            storage = pkgbuildstorage.storage()
            if(cmd_body in storage.packages):
                blog.info("Controller client requested cross build for {}".format(cmd_body))
                
                pkg = storage.get_bpb_obj(cmd_body)
            
                if(pkg is None):
                    return "PKG_BUILD_DAMAGED"

                # get a job obj, use_crosstools = True
                job = manager.new_job(True)

                # TODO: remove seperate build_pkg_name, because pkg contains it.
                job.build_pkg_name = pkg.name
                job.pkg_payload = pkg
                job.requesting_client = client.get_identifier()
                job.set_status("WAITING")

                res = manager.get_queue().add_to_queue(job)
                return res
            else:
                blog.info("Controller client requested release build for invalid package.")
                return "INV_PKG_NAME"
      
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
        # get dependency tree for a given package
        # GET_TREE_STR <NAME>
        #
        case "GET_TREE_STR":
            storage = pkgbuildstorage.storage()

            if(cmd_body in storage.packages):
                blog.info("Calculating dependers for {}..".format(cmd_body))
                
                res = dependency.get_dependency_tree(cmd_body)
                dependency_array = res.get_deps_array()

                return json.dumps(res.get_tree_str())

            else:
                return "INV_PKG_NAME"


        #
        # Rebuild specified package plus all
        # packages that depend on it
        #
        case "REBUILD_DEPENDERS":
            storage = pkgbuildstorage.storage()

            if(cmd_body in storage.packages):
                blog.info("Controller client requested rebuild including dependers for {}".format(cmd_body))

                # get dependency tree
                res = dependency.get_dependency_tree(cmd_body)

                # calculate deps array
                dependency_array = res.get_deps_array()

                # get array of job objects
                jobs = dependency.get_job_array(manager, client, dependency_array)
                
                # calculate blockers on tree
                res.calc_blockers(jobs)
                
                if(not dependency.get_job_by_name(jobs, cmd_body).blocked_by == [ ]):
                    blog.info("Circular dependency detected in packagebuilds. Cannot queue batch job.")
                    return "CIRCULAR_DEPENDENCY"
                
                # add jobs to manager
                for job in jobs:
                    manager.add_job_to_queue(job)

                # queue every job
                for job in jobs:
                    manager.get_queue().add_to_queue(job)
                
                return "BATCH_QUEUED"
            else:
                blog.info("Controller client requested release build for invalid package.")
                return "INV_PKG_NAME"

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
            stor = pkgbuildstorage.storage()
            return json.dumps(stor.packages)

        #
        # Clear completed jobs
        # CLEAR_COMPLETED_JOBS
        #
        case "CLEAR_COMPLETED_JOBS":
            manager.clear_completed_jobs()  
            return "JOBS_CLEARED"
    
        #
        # Get package info
        # PACKAGE_INFO
        #
        case "PACKAGE_INFO":
            stor = pkgbuildstorage.storage()
            if(cmd_body in stor.packages):
                return stor.get_json_bpb(cmd_body)
            else:
                return "INV_PKG"
        
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

            return "BATCH_QUEUED"

        #
        # Releasebuild a solution
        # SUBMIT_SOLUTION_CB <SOL>
        #
        case "SUBMIT_SOLUTION_CB":
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

            return "BATCH_QUEUED"
    
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
                    hash_file = open(job.file_name, "rb")

                    # read chunk by chunk
                    for chunk in iter(lambda: hash_file.read(4096), b""):
                        md5_hash.update(chunk)

                    blog.info("Deploying package to storage..")
                    shutil.move(job.file_name, stor.add_package(job.pkg_payload, md5_hash.hexdigest()))
                    job.set_status("COMPLETED")

                manager.move_inactive_job(job)
            
            client.send_command("CMD_OK")
            blog.info("Client {} is ready for commands.".format(client.get_identifier()))

            client.is_ready = True
            manager.queue.notify_ready()

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
            manager.queue.notify_ready()
            return "CMD_ACK"

        
        #
        # Status update from assigned job: Job accepted by buildbot
        # JOB_ACCEPTED
        #
        case "JOB_ACCEPTED":
            job = manager.get_job_by_client(client)
            

            if(not job is None):
                blog.info("Build job '{}' accepted by {}!".format(job.get_jobid(), client.get_identifier()))
                job.set_status("JOB_ACCEPTED")
                job.job_accepted = True
                return "STATUS_ACK"

            return "NO_JOB"

        #
        # Status update from assigned job: Build environment is ready
        # BUILD_ENV_READY
        #
        case "BUILD_ENV_READY":
            job = manager.get_job_by_client(client)

            if(not job is None):
                blog.info("Build job '{}' completed 'Setup Build Environment' step.".format(job.get_jobid()))
                job.set_status("BUILD_ENV_READY")
                job.job_accepted = True
                return "STATUS_ACK"

            return "NO_JOB"

        #
        # Status update from assigned job: Build job completed.
        # BUILD_COMPLETE
        #
        case "BUILD_COMPLETE":
            job = manager.get_job_by_client(client)

            if(not job is None):
                blog.info("Build job '{}' completed 'Compile source' step.".format(job.get_jobid()))
                job.set_status("BUILD_COMPLETE")
                job.job_accepted = True
                return "STATUS_ACK"

            return "NO_JOB"
        
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
        # Status update from assigned job: Build failed.
        #
        case "BUILD_FAILED":
            job = manager.get_job_by_client(client)

            if(not job is None):
                blog.info("Build job '{}' failed 'Compile source' step.".format(job.get_jobid()))
                job.set_status("BUILD_FAILED")
                job.job_accepted = True
            
            return "STATUS_ACK"


        #
        # Status update from assigned job: Build environment clean up completed.
        # BUILD_CLEAN
        #
        case "BUILD_CLEAN":
            job = manager.get_job_by_client(client)

            if(not job is None):
                blog.info("Build job '{}' completed 'cleanup' step.".format(job.get_jobid()))
                job.set_status("BUILD_CLEAN")
                job.job_accepted = True

            return "STATUS_ACK"
        
        #
        # Switch connection to FILE_TRANSFER_MODE
        # FILE_TRANSFER_MODE <BYTES>
        #
        case "FILE_TRANSFER_MODE":
            try:
                int(cmd_body)
            except Exception:
                return "BYTE_COUNT_ERR"

            job = manager.get_job_by_client(client)

            if(not job is None):
                job.set_status("UPLOADING")
                job.job_accepted = True
                job.file_size = int(cmd_body)
                job.file_name = os.path.join(server.STAGING_AREA, "{}-{}.lfpkg".format(job.build_pkg_name, job.job_id))
                client.file_transfer_mode = True
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
        # Invalid command
        #
        case other:
            blog.debug("Received a malformed command from client {}".format(client.client_uuid))
            return "INV_CMD"
