import os
import json
import blog

from builder import builder
from branchpacket import BranchRequest, BranchResponse, BranchStatus

def handle_command(bc, command) -> BranchRequest:

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

    match cmd_header:
        
        #
        # Build a package using realroot
        #
        case "BUILD_PKG":
            blog.info("Got a job from masterserver. Using realroot")
            return builder.handle_build_request(bc, cmd_body, False)

        #
        # Build a package using crosstools
        # 
        case "BUILD_PKG_CROSS":
            blog.info("Got a job from masterserver. Using crosstools")
            return builder.handle_build_request(bc, cmd_body, True)
        #
        # handles a ping request from overwatch
        #
        case "PING":
            return BranchRequest("PONG", "")
        
        #
        # just in case, but really shouldn't happen.
        #
        case other:
            return "ERR_CMD_UNHANDLED"
            
            
