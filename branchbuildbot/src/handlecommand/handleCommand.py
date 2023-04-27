"""
Handle a command from the masterserver
handle_command() function
"""
import blog
import packagebuild
from branchpacket import BranchRequest

from buildenvmanager import buildenv
from builder import builder

def handle_command(bc, branch_request) -> BranchRequest:
    """
    Handle a command from the masterserver

    :param bc: BranchClient
    :param branch_request: Request to handle
    :return: BranchRequest to send back to the server
    """

    match branch_request.command:
        #
        # Build a package using realroot
        #
        case "BUILD":
            blog.info("Got a job from masterserver. Using realroot")

            if(not "buildtype" in branch_request.payload):
                return BranchRequest("REPORTSTATUSUPDATE", "INVALID_REQUEST")

            if(not "pkgbuild" in branch_request.payload):
                return BranchRequest("REPORTSTATUSUPDATE", "INVALID_REQUEST")

            try:
                buildtype = branch_request.payload["buildtype"]
                pkgbuild = packagebuild.package_build.from_dict(branch_request.payload["pkgbuild"])
            except Exception:
                return BranchRequest("REPORTSTATUSUPDATE", "INVALID_REQUEST")
            
            b: Builder = builder.Builder(bc)

            match b.build(pkgbuild, buildtype == "CROSS"):
                case True:
                    blog.info("Build job completed successfully.")
                            
                case False:
                    blog.warn("Build job failed.")
                    bc.report_build_status_update("BUILD_FAILED")
            
            buildenv.clean_env()
            bc.send_recv_msg(BranchRequest("SIGREADY", ""))
            return None

        #
        # handles a ping request from overwatch
        #
        case "PING":
            return BranchRequest("PONG", "")
        
        #
        # just in case, but really shouldn't happen.
        #
        case other:
            return BranchRequest("", "")
            
            
