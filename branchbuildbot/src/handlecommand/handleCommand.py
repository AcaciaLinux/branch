from log import blog

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
            blog.info("Relase build requested. Json: {}".format(cmd_body))
            print()
            print("STUB: build pkg")
            print()
            # We completed the build job successfully. Send SIG_READY
            return "SIG_READY"
        else:
            # No json package build submitted. Tell server we failed.
            return "ERR_CMD_UNHANDLED"

    else:
        # The server sent us an invalid or unimplemented command. Tell the server we failed.
        blog.error("The build server sent us an invalid command. Version mismatch?")
        blog.error("Sending server error response.")
        blog.error("Trying to continue..")
        return "ERR_CMD_UNHANDLED"
