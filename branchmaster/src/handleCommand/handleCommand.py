import json
import os
import time
import selectors

import main
from config import config
from log import blog
from localstorage import packagestorage 
from localstorage import pkgbuildstorage
from package import build
from manager import queue
from manager import jobs
from dependency import dependency

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

    
    if(client.client_type is None):
        return handle_command_untrusted(manager, client, cmd_header, cmd_body)
    elif(client.client_type == "CONTROLLER"):
        return handle_command_controller(manager, client, cmd_header, cmd_body)
    elif(client.client_type == "BUILD"):
        return handle_command_build(manager, client, cmd_header, cmd_body)
    else:
        return None
  
def handle_command_untrusted(manager, client, cmd_header, cmd_body):
    bconf = config.branch_options()

    #
    # Used by a client to send it's auth key
    #
    if(cmd_header == "AUTH"):
        if(client.is_authenticated):
            return "ALREADY_AUTHENTICATED"
        else:
            blog.debug("Client '{}' authenticating with key: {}".format(client.get_identifier(), cmd_body))
            if(cmd_body in bconf.authkeys):
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
    elif(cmd_header == "SET_MACHINE_TYPE"):
        
        #
        # Check if the server allows untrusted clients
        # or the client is authenticated
        #
        if(client.is_authenticated or bconf.untrustedclients):
            if(cmd_body == "CONTROLLER"):
                blog.info("Machine type assigned. Client '{}' is authenticated as controller client type.".format(client.get_identifier()))
                client.client_type = "CONTROLLER"
            elif(cmd_body == "BUILD"):
                blog.info("Machine type assigned. Client '{}' is authenticated as build client type.".format(client.get_identifier()))
                client.client_type = "BUILD"
            else:
                return "INV_MACHINE_TYPE"

            return "CMD_OK"
        else:
            return "AUTH_REQUIRED"

    else:
        blog.debug("Received a malformed command from client {}".format(client.client_uuid))
        return "INV_CMD"

def handle_command_controller(manager, client, cmd_header, cmd_body):
    #
    # Used by a client to set it's display name
    # SET_MACHINE_NAME <NAME>
    #
    if(cmd_header == "SET_MACHINE_NAME"):
        blog.info("Client name changed. Client '{}' is now known as '{}'".format(client.get_identifier(), cmd_body))
        client.client_name = cmd_body
        return "CMD_OK"
   
    #
    # checkout a package build file
    #
    elif(cmd_header == "CHECKOUT_PACKAGE"):
        storage = pkgbuildstorage.storage()

        if(cmd_body in storage.packages):
            blog.info("Client {} checked out package '{}'!".format(client.get_identifier(), cmd_body))
            return storage.get_json_bpb(cmd_body)
        else:
            return "INV_PKG_NAME"

    #
    # submit a package build file
    #
    elif(cmd_header == "SUBMIT_PACKAGE"):
        storage = pkgbuildstorage.storage()

        json_bpb = json.loads(cmd_body)
        if(json_bpb is None):
            return "INV_PKG_BUILD"

        bpb = build.parse_build_json(json_bpb)
        if(bpb.name == "" or bpb.version == "" or bpb.real_version == ""):
            return "INV_PKG_BUILD"

        tdir = storage.create_stor_directory(bpb.name)

        bpb_file = os.path.join(tdir, "package.bpb")
        if(os.path.exists(bpb_file)):
            os.remove(bpb_file)
       
        build.write_build_file(bpb_file, bpb)
        return "CMD_OK"
 
    #
    # Controller client requested clean release build
    #
    elif(cmd_header == "RELEASE_BUILD"):
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
    #
    elif(cmd_header == "CROSS_BUILD"):
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
    #
    elif(cmd_header == "VIEW_LOG"):
        if(cmd_body == ""):
            return "INV_JOB_ID"
        
        job = manager.get_job_by_id(cmd_body)
        
        if(job is None):
            return "INV_JOB_ID"
        
        if(job.build_log is None):
            return "NO_LOG"

        return json.dumps(job.build_log)

    elif(cmd_header == "VIEW_SYS_EVENTS"):
        return json.dumps(manager.system_events)

    #
    # Rebuild specified package plus all
    # packages that depend on it
    #
    elif(cmd_header == "REBUILD_DEPENDERS"):
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
            
            # queue every job
            for job in jobs:
                manager.get_queue().add_to_queue(job)
            
            return "BATCH_QUEUED"
        else:
            blog.info("Controller client requested release build for invalid package.")
            return "INV_PKG_NAME"

    #
    # Get all completed build jobs 
    #
    elif(cmd_header == "COMPLETED_JOBS_STATUS"):
        completed_jobs = manager.get_completed_jobs()
        return json.dumps([obj.get_info_dict() for obj in completed_jobs])
 
    #
    # Get all currently running build jobs 
    #
    elif(cmd_header == "RUNNING_JOBS_STATUS"):
        running_jobs = manager.get_running_jobs()
        return json.dumps([obj.get_info_dict() for obj in running_jobs])

    #
    # Get queued jobs 
    #
    elif(cmd_header == "QUEUED_JOBS_STATUS"):
        queued_jobs = manager.get_queued_jobs()
        return json.dumps([obj.get_info_dict() for obj in queued_jobs])


    #
    # Get connected controller type clients
    #
    elif(cmd_header == "CONNECTED_CONTROLLERS"):
        clients = manager.get_controller_names()
        return json.dumps(clients)

    #
    # Get connected build type clients
    #
    elif(cmd_header == "CONNECTED_BUILDBOTS"):
        buildbots = manager.get_buildbot_names()
        return json.dumps(buildbots)

    #
    # Get a list of all managed packages
    #
    elif(cmd_header == "MANAGED_PACKAGES"):
        stor = packagestorage.storage()
        return json.dumps(stor.packages)
    
    #
    # Get a list of all managed packagebuilds
    #
    elif(cmd_header == "MANAGED_PKGBUILDS"):
        stor = pkgbuildstorage.storage()
        return json.dumps(stor.packages)

    #
    # Clear completed jobs
    #
    elif(cmd_header == "CLEAR_COMPLETED_JOBS"):
        manager.clear_completed_jobs()  
        return "JOBS_CLEARED"
    
    elif(cmd_header == "PACKAGE_INFO"):
        stor = pkgbuildstorage.storage()

        if(cmd_body in stor.packages):
            return stor.get_json_bpb(cmd_body)
        else:
            return "INV_PKG"
    
    #
    # Cancel queued jobs
    #
    elif(cmd_header == "CANCEL_QUEUED_JOB"):
        if(cmd_body == ""):
            return "INV_JOB_ID"
        
        job = manager.get_job_by_id(cmd_body)
        
        if(job is None):
            return "INV_JOB_ID"
       
        manager.cancel_queued_job(job) 
        return "JOB_CANCELED"

    #
    # Cancel all queued jobs
    #
    elif(cmd_header == "CANCEL_ALL_QUEUED_JOBS"):
        manager.cancel_all_queued_jobs()
        return "JOBS_CANCELED"

    #
    # Invalid command
    #
    else:
        blog.debug("Received a malformed command from client {}".format(client.client_uuid))
        return "INV_CMD"



def handle_command_build(manager, client, cmd_header, cmd_body):
    #
    # Used by a client to set it's display name
    # SET_MACHINE_NAME <NAME>
    #
    if(cmd_header == "SET_MACHINE_NAME"):
        blog.info("Client name changed. Client '{}' is now known as '{}'".format(client.get_identifier(), cmd_body))
        client.client_name = cmd_body
        return "CMD_OK"

    # 
    # Build client sends ready signal
    #
    elif(cmd_header == "SIG_READY"):
        # check if cli just finished a job or not
        job = manager.get_job_by_client(client)
        if(not job is None):
            blog.info("Build job '{}' completed.".format(job.get_jobid()))
            if(job.get_status() == "BUILD_FAILED"):
                job.set_status("FAILED")
            else:
                job.set_status("COMPLETED")

            manager.move_inactive_job(job)
        
        client.send_command("CMD_OK")
        blog.info("Client {} is ready for commands.".format(client.get_identifier()))

        client.is_ready = True
        manager.queue.notify_ready()
        return None
    
    #
    # Status update from assigned job: Job accepted by buildbot
    #
    elif(cmd_header == "JOB_ACCEPTED"):
        job = manager.get_job_by_client(client)

        if(not job is None):
            blog.info("Build job '{}' accepted by {}!".format(job.get_jobid(), client.get_identifier()))
            job.set_status("JOB_ACCEPTED")
            return "STATUS_ACK"

        return "NO_JOB"


    #
    # Status update from assigned job: Build environment is ready
    #
    elif(cmd_header == "BUILD_ENV_READY"):
        job = manager.get_job_by_client(client)

        if(not job is None):
            blog.info("Build job '{}' completed 'Setup Build Environment' step.".format(job.get_jobid()))
            job.set_status("BUILD_ENV_READY")
            return "STATUS_ACK"

        return "NO_JOB"

    #
    # Status update from assigned job: Build job completed.
    #
    elif(cmd_header == "BUILD_COMPLETE"):
        job = manager.get_job_by_client(client)

        if(not job is None):
            blog.info("Build job '{}' completed 'Compile source' step.".format(job.get_jobid()))
            job.set_status("BUILD_COMPLETE")
            return "STATUS_ACK"

        return "NO_JOB"

    elif(cmd_header == "SUBMIT_LOG"):
        job = manager.get_job_by_client(client)

        if(not job is None):
            blog.info("Build job '{}' log received.".format(job.get_jobid()))
            job.set_buildlog(json.loads(cmd_body))
            return "LOG_OK"

        return "NO_JOB"

    #
    # Status update from assigned job: Build failed.
    #
    elif(cmd_header == "BUILD_FAILED"):
        job = manager.get_job_by_client(client)

        if(not job is None):
            blog.info("Build job '{}' failed 'Compile source' step.".format(job.get_jobid()))
            job.set_status("BUILD_FAILED")

        return "STATUS_ACK"


    #
    # Status update from assigned job: Build environment clean up completed.
    #
    elif(cmd_header == "BUILD_CLEAN"):
        job = manager.get_job_by_client(client)

        if(not job is None):
            blog.info("Build job '{}' completed 'cleanup' step.".format(job.get_jobid()))
            job.set_status("BUILD_CLEAN")

        return "STATUS_ACK"

    elif(cmd_header == "FILE_TRANSFER_MODE"):
        job = manager.get_job_by_client(client)

        if(not job is None):
            job.set_status("UPLOADING")

            job.file_size = int(cmd_body)
            
            stor = packagestorage.storage()
            job.file_name = stor.add_package(job.pkg_payload)

            client.file_transfer_mode = True
            return "ACK_FILE_TRANSFER"

        else:
            return "NO_JOB"

    elif(cmd_header == "REPORT_SYS_EVENT"):
        if(cmd_body is None):
            return "EMPTY_SYS_EVENT"

        blog.info("Received System Event report from {}.".format(client.get_identifier()))
        manager.system_events.append("{} => {}".format(client.get_identifier(), cmd_body))
        return "RECV_SYS_EVENT"

    #
    # Invalid command
    #
    else:
        blog.debug("Received a malformed command from client {}".format(client.client_uuid))
        return "INV_CMD"
