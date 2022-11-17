import main
import json

from log import blog
from bsocket import connect 
from package import build 

#
# checkout package
#
def checkout_package(s, pkg_name):
    bpb_resp = connect.send_msg(s, "CHECKOUT_PACKAGE {}".format(pkg_name))
    
    # check if package is valid
    if(bpb_resp == "INV_PKG_NAME"):
        blog.error("The specified package could not be found.")
        return
    
    json_bpb = json.loads(bpb_resp)
    bpb = build.parse_build_json(json_bpb)
    build.create_pkg_workdir(bpb)

#
# Submit a package build from cwd to server
#
def submit_package(s):
    bpb = build.parse_build_file("package.bpb")
    if(bpb == -1):
        return -1

    json_str = bpb.get_json()
    resp = connect.send_msg(s, "SUBMIT_PACKAGE {}".format(json_str))
    
    if(resp == "CMD_OK"):
        blog.info("Package submission accepted by server.")
    else:
        blog.error("An error occured: {}".format(resp))

#
# Request a release build from a specified package
#
def release_build(s, pkg_name):
    resp = connect.send_msg(s, "RELEASE_BUILD {}".format(pkg_name))

    if(resp == "BUILD_REQ_SUBMIT_IMMEDIATELY"):
        blog.info("The package build was immediately handled by a ready build bot.")
    elif(resp == "BUILD_REQ_QUEUED"):
        blog.info("No buildbot is currently available to handle the build request. Build request added to queue.")
    elif(resp == "INV_PKG_NAME"):
        blog.error("Invalid package name.")
    elif(resp == "PKG_BUILD_DAMAGED"):
        blog.error("The packagebuild you attempted to queue is damaged.")
#
# Request a cross build from a specified package
#
def cross_build(s, pkg_name):
    if(s is None):
        blog.error("Connection refused.")
        return

    resp = connect.send_msg(s, "CROSS_BUILD {}".format(pkg_name))

    if(resp == "BUILD_REQ_SUBMIT_IMMEDIATELY"):
        blog.info("The package build was immediately handled by a ready build bot.")
    elif(resp == "BUILD_REQ_QUEUED"):
        blog.info("No buildbot is currently available to handle the build request. Build request added to queue.")
    elif(resp == "INV_PKG_NAME"):
        blog.error("Invalid package name.")
    elif(resp == "PKG_BUILD_DAMAGED"):
        blog.error("The packagebuild you attempted to queue is damaged.")
#
# get job status from server
#
def build_status(s):
    resp = connect.send_msg(s, "RUNNING_JOBS_STATUS")
    running_jobs = json.loads(resp)

    resp = connect.send_msg(s, "COMPLETED_JOBS_STATUS")
    completed_jobs = json.loads(resp)

    resp = connect.send_msg(s, "QUEUED_JOBS_STATUS")
    queued_jobs = json.loads(resp)

    if(running_jobs):
        print()
        print("RUNNING JOBS:")
        print ("{:<20} {:<15} {:<40} {:<10}".format("NAME", "STATUS", "ID", "REQUESTED BY"))

        for job in running_jobs:
            print ("{:<20} {:<15} {:<40} {:<10}".format(job['build_pkg_name'], job['job_status'], job['job_id'], job['requesting_client']))

    if(completed_jobs):
        print()
        print("COMPLETED JOBS:")
        print ("{:<20} {:<15} {:<40} {:<10}".format("NAME", "STATUS", "ID", "REQUESTED BY"))

        for job in completed_jobs:
            if(job['job_status'] == "FAILED"):
                print ("{:<20} \033[91m{:<15}\033[0m {:<40} {:<10}".format(job['build_pkg_name'], job['job_status'], job['job_id'], job['requesting_client']))
            else:
                print ("{:<20} \033[92m{:<15}\033[0m {:<40} {:<10}".format(job['build_pkg_name'], job['job_status'], job['job_id'], job['requesting_client']))


    if(queued_jobs):
        print()
        print("QUEUED JOBS:")
        print ("{:<20} {:<15} {:<40} {:<10}".format("NAME", "STATUS", "ID", "REQUESTED BY"))

        for job in queued_jobs:
            print ("{:<20} {:<15} {:<40} {:<10}".format(job['build_pkg_name'], job['job_status'], job['job_id'], job['requesting_client']))

    if(not completed_jobs and not running_jobs and not queued_jobs):
        blog.info("No jobs.")

#
# Get connected buildbots / controllers
#
def client_status(s):
    resp = connect.send_msg(s, "CONNECTED_CONTROLLERS")
    controllers = json.loads(resp)

    resp = connect.send_msg(s, "CONNECTED_BUILDBOTS")
    buildbots = json.loads(resp)
    print()

    print("CONTROLLER CLIENTS:")
    for name in controllers:
        print(name, end=' ')
    print()

    print()
    print()

    print("BUILDBOT CLIENTS:")
    for name in buildbots:
        print(name, end=' ')
    print()

#
# get build log
#
def get_buildlog(s, job_id):
    resp = connect.send_msg(s, "VIEW_LOG {}".format(job_id))
    
    if(resp == "INV_JOB_ID" or resp == "NO_LOG"):
        blog.error("No build log available for specified job id. Is it still running?")
        return

    log = json.loads(resp)

    print("\nBUILD LOG FOR '{}':\n".format(job_id))
    for line in log:
        print(line)

def clear_completed_jobs(s):
    resp = connect.send_msg(s, "CLEAR_COMPLETED_JOBS")

    if(not resp == "JOBS_CLEARED"):
        blog.error("An error occurred: {}".format(resp))
        return

    return

def get_managed_packages(s):
    resp = connect.send_msg(s, "MANAGED_PACKAGES")
    
    jsonp = json.loads(resp)

    print("Managed packages:")
    print()

    for count, item in enumerate(sorted(jsonp), 1):
        print(item.ljust(30), end="")
        if(count % 4 == 0):
           print()

    print()
    return

def get_managed_pkgbuilds(s):
    resp = connect.send_msg(s, "MANAGED_PKGBUILDS")

    jsonp = json.loads(resp)

    print("Managed pkgbuilds:\n")

    for count, item in enumerate(sorted(jsonp), 1):
        print(item.ljust(30), end="")
        if(count % 4 == 0):
           print()

    print()
    return


def get_diff_pkg(s):
    resp = connect.send_msg(s, "MANAGED_PACKAGES")
    pkgs = json.loads(resp)

    resp = connect.send_msg(s, "MANAGED_PKGBUILDS")
    pkg_builds = json.loads(resp)

    print("pkg / pkgbuild difference:\n")

    for count, item in enumerate(sorted(pkg_builds), 1):

        if(item in pkgs):
            print('\033[92m', end="")
        else:
            print('\033[91m', end="")

        print(item.ljust(30), end="")
        print('\033[0m', end="")
        if(count % 4 == 0):
           print()

    print()

