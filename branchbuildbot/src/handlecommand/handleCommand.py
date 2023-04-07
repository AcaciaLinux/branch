import blog
import packagebuild

from builder import builder
from branchpacket import BranchRequest

def handle_command(bc, branch_request) -> BranchRequest:
     
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

            match builder.handle_build_request(bc, pkgbuild, buildtype == "CROSS"):

                case True:
                    blog.info("Build job completed successfully.")
            
                case False:
                    blog.warn("Build job failed.")
            
                case "CRIT_ERR":
                    blog.error("Build environment damaged.")
                    return "CRIT_ERR"

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
            
            
