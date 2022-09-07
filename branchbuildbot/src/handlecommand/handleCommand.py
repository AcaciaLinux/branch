import os
import json

from buildenvmanager import buildenv
from log import blog
from package import build
from bsocket import connect 
from buildenvmanager import buildenv
from package import leafpkg

def handle_command(socket, command):

    # Find the first space
    cmd_header_loc = command.find(" ")
    cmd_header = ""
    cmd_body = ""

    # One word comamnd
    if(cmd_header_loc == -1):
        cmd_header = command
        cmd_body = None
    else:
        cmd_header = command[0:cmd_header_loc]
        cmd_body = command[cmd_header_loc+1:len(command)]

    
    # BUILD_PKG request
    if(cmd_header == "BUILD_PKG"):
        if(not cmd_body is None):
            json_obj = json.loads(cmd_body)

            job_id = json_obj['job_id']
            blog.info("Got a job from masterserver. Job ID: '{}'".format(job_id))

            buildenv.setup_env(False) 
            rootdir = buildenv.get_build_path()
            
            # create temp workdir directory
            builddir = os.path.join(rootdir, "branchbuild/")
            if(not os.path.exists(builddir)):
                os.mkdir(builddir)

            # parse the package build we got
            package_build = build.parse_build_json(json_obj)
            
            # Write the file to /branchbuild/ inside our build environment
            build.write_build_file(os.path.join(builddir, "package.bpb"), package_build)

            # notify server build env is ready, about to start build
            connect.send_msg(socket, "BUILD_ENV_READY")
    
            # run build step
            res = build.build(builddir, package_build)  
            
            if(res == "BUILD_COMPLETE"):
                connect.send_msg(socket, "BUILD_COMPLETE")
            else:
                connect.send_msg(socket, "BUILD_FAILED")

                # Clean build environment..
                blog.info("Cleaning up build environment..")
                buildenv.clean_env()
                return "SIG_READY"
            
            pkg_file = leafpkg.create_tar_package(builddir, package_build)
            
            file_size = os.path.getsize(pkg_file)
            blog.info("Package file size is {} bytes".format(file_size))
            
            # ask the server to switch into file_transfer_mode
            res = connect.send_msg(socket, "FILE_TRANSFER_MODE {}".format(file_size))
            
            # if we got any other response, we couldn't switch mode
            if(not res == "ACK_FILE_TRANSFER"):
                blog.error("Server did not switch to upload mode: {}".format(res))
                blog.error("Returning to ready-state.")
                connect.send_msg(socket, "BUILD_FAILED")

                # Clean build environment..
                blog.info("Cleaning up build environment..")
                buildenv.clean_env()
                return "SIG_READY"
            
            # send file over socket
            res = connect.send_file(socket, pkg_file)            

            if(not res == "UPLOAD_ACK"):
                blog.error("Uploading the package file failed.")
                blog.error("Returning to ready-state")

                # notify build failure
                connect.send_msg(socket, "BUILD_FAILED")
                
                # Clean build environment..
                blog.info("Cleaning up build environment..")
                buildenv.clean_env()
                return "SIG_READY"
            else:
                blog.info("File upload completed!")

            # Clean build environment..
            blog.info("Cleaning up build environment..")
            buildenv.clean_env()
            
            connect.send_msg(socket, "BUILD_CLEAN")

            # We completed the build job. Send SIG_READY
            blog.info("Build job completed.")
            return "SIG_READY"
        else:
            # No json package build submitted. Tell server we failed.
            return "ERR_BUILD_INV"
    
    else:
        # The server sent us an invalid or unimplemented command. Tell the server we failed.
        blog.error("The build server sent us an invalid command. Version mismatch?")
        blog.error("Sending server error response.")
        blog.error("Trying to continue..")
        return "ERR_CMD_UNHANDLED"
