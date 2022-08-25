import json
import os
import time
import selectors

import main
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

    # TODO: Login system
    #blog.info("Machine validation skipped. Untrusted clients are permitted.")

    #
    # Used by a client to set it's type
    # SET_MACHINE_TYPE <TYPE>
    # (controller, build)
    #
    if(cmd_header == "SET_MACHINE_TYPE"):
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

            # get a job obj
            job = manager.new_job()

            # TODO: remove seperate build_pkg_name, because pkg contains it.
            job.build_pkg_name = pkg.name
            job.pkg_payload = pkg
            job.requesting_client = client.get_identifier()
            job.set_status("WAITING")

            res = manager.get_queue().add_to_queue(manager, job)
            return res
        else:
            blog.info("Controller client requested release build for invalid package.")
            return "INV_PKG_NAME"
    
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

            #TODO: refactor needed
            
            # calculate deps array
            dependency_array = res.get_deps_array()
            
            # get array of job objects
            jobs = dependency.get_job_array(manager, client, dependency_array)
            
            # calculate blockers on tree
            res.calc_blockers(jobs)
            
            # queue every job
            for job in jobs:
                manager.get_queue().add_to_queue(manager, job)
            
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
    # test
    #
    elif(cmd_header == "TEST"):
        stor = packagestorage.storage()
        meta_inf = stor.get_all_package_meta()

        for meta in meta_inf:
            real_version = meta.get_latest_real_version()
            print("{};{};{};{};{}".format(meta.get_name(), real_version, meta.get_version(real_version), meta.get_description(), meta.get_dependencies(real_version)))

        return "BLA"

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

        blog.info("Client {} is ready for commands.".format(client.get_identifier()))
        client.is_ready = True
        client.send_command("CMD_OK")

        # TODO:
        # - Regenerate Package build, if the build job succeeded.
        # - How to transfer leaf package..?

        manager.queue.notify_ready(manager)
        return None

    #
    # Status update from assigned job: Build environment is ready
    #
    elif(cmd_header == "BUILD_ENV_READY"):
        job = manager.get_job_by_client(client)

        if(not job is None):
            blog.info("Build job '{}' completed 'Setup Build Environment' step.".format(job.get_jobid()))
            job.set_status("BUILD_ENV_READY")

        return "STATUS_ACK"

    #
    # Status update from assigned job: Build job completed.
    #
    elif(cmd_header == "BUILD_COMPLETE"):
        job = manager.get_job_by_client(client)

        if(not job is None):
            blog.info("Build job '{}' completed 'Compile source' step.".format(job.get_jobid()))
            job.set_status("BUILD_COMPLETE")

        return "STATUS_ACK"

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

            # ack
            return "ACK_FILE_TRANSFER"

        else:
            return "NO_JOB"

    #
    # Invalid command
    #
    else:
        blog.debug("Received a malformed command from client {}".format(client.client_uuid))
        return "INV_CMD"
