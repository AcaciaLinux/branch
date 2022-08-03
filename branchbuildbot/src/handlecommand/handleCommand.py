import os
import json
from log import blog
from package import build


def handle_command(command):

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
            blog.info("Release build requested. Assigned job id: {}".format(cmd_body))

            # create temp bild directory
            if(not os.path.exists("/tmp/branch")):
                os.mkdir("/tmp/branch/")
            
            build_dir = os.path.join("/tmp/branch/", job_id)
            os.mkdir(build_dir)

            bpb = build.parse_build_json(json_obj)

            build.write_build_file(os.path.join(build_dir, "package.bpb"), bpb)

            # We completed the build job. Send SIG_READY
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
