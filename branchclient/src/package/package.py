import main
import json
from log import blog
from bsocket import connect 
from package import build 

def checkout_package(conf, pkg_name):
    s = connect.connect(conf.serveraddr, conf.serverport, conf.identifier, main.B_TYPE)
    
    bpb_resp = connect.send_msg(s, "CHECKOUT_PACKAGE {}".format(pkg_name))
    
    # check if package is valid
    if(bpb_resp == "INV_PKG_NAME"):
        blog.error("The specified package could not be found.")
        return
    
    json_bpb = json.loads(bpb_resp)
    bpb = build.parse_build_json(json_bpb)
    build.create_pkg_workdir(bpb)

def release_build(conf, pkg_name):
    s = connect.connect(conf.serveraddr, conf.serverport, conf.identifier, main.B_TYPE)

    resp = connect.send_msg(s, "RELEASE_BUILD {}".format(pkg_name))

    if(resp == "BUILD_REQ_SUBMIT_IMMEDIATELY"):
        blog.info("The package build was immediately handled by a ready build bot.")
    elif(resp == "BUILD_REQ_QUEUED"):
        blog.info("No buildbot is currently available to handle the build request. Build request added to queue.")
    elif(resp == "INV_PKG_NAME"):
        blog.error("Invalid package name.")
        
def submit_package(conf):
    s = connect.connect(conf.serveraddr, conf.serverport, conf.identifier, main.B_TYPE)
    
    bpb = build.parse_build_file("package.bpb")
    if(bpb == -1):
        return -1

    json_str = bpb.get_json()
    resp = connect.send_msg(s, "SUBMIT_PACKAGE {}".format(json_str))
    
    if(resp == "CMD_OK"):
        blog.info("Package submission accepted by server.")
    else:
        blog.error("An error occured: {}".format(resp))

def build_status(conf):
    s = connect.connect(conf.serveraddr, conf.serverport, conf.identifier, main.B_TYPE)

    resp = connect.send_msg(s, "RUNNING_JOBS_STATUS")
    running_jobs = json.loads(resp)

    resp = connect.send_msg(s, "COMPLETED_JOBS_STATUS")
    completed_jobs = json.loads(resp)

    resp = connect.send_msg(s, "QUEUED_JOBS_STATUS")
    queued_jobs = json.loads(resp)

    if(running_jobs):
        print()
        print("RUNNING JOBS:")
        print ("{:<8} {:<15} {:<40} {:<10}".format("NAME", "STATUS", "ID", "REQUESTED BY"))

        for job in running_jobs:
            print ("{:<8} {:<15} {:<40} {:<10}".format(job['build_pkg_name'], job['job_status'], job['job_id'], job['requesting_client']))
    

    if(completed_jobs):
        print()
        print("COMPLETED JOBS:")
        print ("{:<8} {:<15} {:<40} {:<10}".format("NAME", "STATUS", "ID", "REQUESTED BY"))

        for job in completed_jobs:
            print ("{:<8} {:<15} {:<40} {:<10}".format(job['build_pkg_name'], job['job_status'], job['job_id'], job['requesting_client']))


    if(queued_jobs):
        print()
        print("QUEUED JOBS:")
        for job in queued_jobs:
            print("- {}".format(job['pkg_name']))           

    if(not completed_jobs and not running_jobs and not queued_jobs):
        blog.info("No jobs.")
