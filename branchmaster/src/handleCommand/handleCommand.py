import json
import os
import main
from log import blog
from localstorage import localstorage
from package import build
from manager import queue

def handle_command(manager, client, command):
    command = command.decode("utf-8")

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
    #blog.info("Machine validation failed, but untrusted clients are permitted.")

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
        storage = localstorage.storage()

        if(cmd_body in storage.packages):
            blog.info("Client {} checked out package '{}'!".format(client.get_identifier(), cmd_body))
            return storage.get_json_bpb(cmd_body)
        else:
            return "INV_PKG_NAME"

    #
    # submit a package build file
    #
    elif(cmd_header == "SUBMIT_PACKAGE"):
        json_bpb = json.loads(cmd_body)
        bpb = build.parse_build_json(json_bpb)
        tdir = build.create_stor_directory(bpb.name)
        
        bpb_file = os.path.join(tdir, "package.bpb")
        if(os.path.exists(bpb_file)):
            os.remove(bpb_file)
       
        build.write_build_file(bpb_file, bpb)
        return "CMD_OK"
    
    #
    # Controller client requested clean release build
    #
    elif(cmd_header == "RELEASE_BUILD"):
        storage = localstorage.storage()
        if(cmd_body in storage.packages):
            blog.info("Controller client requested release build for {}".format(cmd_body))
            res = manager.get_queue().add_to_queue(manager, cmd_body, client)
            return res
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
            job.set_completed = True
            if(not job.get_status == "FAILED"):
                job.set_status("COMPLETED")

            manager.move_inactive_job(job)

        blog.info("Client {} is ready for commands.".format(client.get_identifier()))
        client.is_ready = True
        client.send_command("CMD_OK")
        manager.queue.notify_ready(manager)
        return None

    elif(cmd_header == "BUILD_ENV_READY"):
        job = manager.get_job_by_client(client)

        if(not job is None):
            blog.info("Build job '{}' completed 'Setup Build Environment' step.".format(job.get_jobid()))
            job.set_status("BUILD_ENV_READY")

        return "STATUS_ACK"

    elif(cmd_header == "BUILD_COMPLETE"):
        job = manager.get_job_by_client(client)

        if(not job is None):
            blog.info("Build job '{}' completed 'Compile source' step.".format(job.get_jobid()))
            job.set_status("BUILD_COMPLETE")

        return "STATUS_ACK"

    elif(cmd_header == "BUILD_FAILED"):
        job = manager.get_job_by_client(client)

        if(not job is None):
            blog.info("Build job '{}' failed 'Compile source' step.".format(job.get_jobid()))
            job.set_status("BUILD_FAILED")

        return "STATUS_ACK"
 
    elif(cmd_header == "BUILD_CLEAN"):
        job = manager.get_job_by_client(client)

        if(not job is None):
            blog.info("Build job '{}' completed 'cleanup' step.".format(job.get_jobid()))
            job.set_status("BUILD_CLEAN")

        return "STATUS_ACK"
    
    #
    # Invalid command
    #
    else:
        blog.debug("Received a malformed command from client {}".format(client.client_uuid))
        return "INV_CMD"



