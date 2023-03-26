import blog
import json
import branchclient
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

    blog.info("Connecting to {}:{} using clientname {}".format(host, port, clientname))
    bc = branchclient.branchclient(host, int(port), clientname, authkey, "CONTROLLER")
    
    blog.info("Fetching available packages..")
    managed_packagebuilds = json.loads(bc.send_recv_msg("MANAGED_PKGBUILDS"))
    
    curr_time = time.strftime("%d.%m.%g-%H:%M:%S", time.localtime())
    
    target_dir = os.path.join(LAUNCHDIR, "backup-" + curr_time)

    blog.info("Beginning export to {}...".format(target_dir))
    pkgbuilds = [ ]

    for pkgbuild_name in managed_packagebuilds:
        blog.info("Checking out: {}".format(pkgbuild_name))
        resp = bc.send_recv_msg("CHECKOUT_PACKAGE {}".format(pkgbuild_name))
        
        # check if package is valid
        if(resp == "INV_PKG_NAME"):
            blog.error("Packagebuild {} could not be found.".format(pkgbuild_name))
            return

        if(resp == "INV_PKG"):
            blog.error("Packagebuild {} is damaged and could not be checked out.".format(pkgbuild_name))
            return
        
        pkgbuilds.append(packagebuild.package_build.from_json(resp))

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



if(__name__ == "__main__"):
    main()
