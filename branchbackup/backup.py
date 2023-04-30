import blog
import json
import branchclient
from branchpacket import BranchRequest, BranchResponse, BranchStatus
import sys
import os
import packagebuild
import time

LAUNCHDIR = os.getcwd()

def main():
    blog.info("Initializing..")
    
    # Host, port, Clientname, Authkey 
    if(len(sys.argv) != 5):
        blog.error("Usage: backup.py [Host] [Port] [Clientname] [Authkey]")
        return -1
    
    host = sys.argv[1]
    port = sys.argv[2]
    clientname = sys.argv[3]
    authkey = sys.argv[4]

    blog.info(f"Connecting to {host}:{port} using clientname '{clientname}'")
    bc = branchclient.branchclient(host, int(port), clientname, authkey, "CONTROLLER")
    
    blog.info("Fetching available packages..")
    managed_packagebuilds: BranchResponse = bc.send_recv_msg(BranchRequest("GETMANAGEDPKGBUILDS", "")).payload
    
    curr_time = time.strftime("%d.%m.%g-%H:%M:%S", time.localtime())
    target_dir = os.path.join(LAUNCHDIR, "backup-" + curr_time)

    blog.info(f"Beginning export to {target_dir}...")
    pkgbuilds = [ ]

    for pkgbuild_name in managed_packagebuilds:
        blog.info("Checking out: {}".format(pkgbuild_name))
        resp = bc.send_recv_msg(BranchRequest("CHECKOUT", pkgbuild_name))
        
        match resp.statuscode:

            case BranchStatus.OK:
                pkgbuilds.append(packagebuild.package_build.from_dict(resp.payload))

            case other:
                blog.error(f"Packagebuild '{pkgbuild_name}' could not be checked out: {resp.payload}")
                return

    blog.info("{} package builds fetched.".format(len(pkgbuilds)))
    blog.info("Saving packagebuilds to {}".format(target_dir))
    try:
        os.mkdir(target_dir)
    except Exception:
        blog.error("Could not create export directory.")
        return

    for pkgbuild in pkgbuilds:
        target_sub_dir = os.path.join(target_dir, pkgbuild.name)
        target_file = os.path.join(target_sub_dir, "package.bpb")
        
        try:
            os.mkdir(target_sub_dir)
            pkgbuild.write_build_file(target_file)
        except Exception:
            blog.error("Could not write to disk. Aborting")
            return
    
    blog.info("Export completed.")
    bc.disconnect()



if(__name__ == "__main__"):
    main()
