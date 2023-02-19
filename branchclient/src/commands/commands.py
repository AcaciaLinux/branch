import main
import json
import os
import blog
import packagebuild
import time

from bsocket import connect 
from utils import inpututil

#
# checkout package
#
def checkout_package(s, pkg_name):
    bpb_resp = connect.send_msg(s, "CHECKOUT_PACKAGE {}".format(pkg_name))
    
    # check if package is valid
    if(bpb_resp == "INV_PKG_NAME"):
        blog.error("The specified package could not be found.")
        return

    if(bpb_resp == "INV_PKG"):
        blog.error("The package build is damaged and could not be checked out.")
        return

    pkgbuild = packagebuild.package_build.from_json(bpb_resp)

    target_file = os.path.join(pkg_name, "package.bpb")
    
    if(not os.path.exists(pkg_name)):
        os.mkdir(pkg_name)

    if(os.path.exists(target_file)):
        if(not inpututil.ask_choice("Checking out will overwrite your local working copy. Continue?")):
            blog.error("Aborting.")
            return

    pkgbuild.write_build_file(target_file)
    blog.info("Successfully checkout out package {}!".format(pkg_name))
        

#
# Submit a package build from cwd to server
#
def submit_package(s):
    bpb = packagebuild.package_build.from_file("package.bpb")
    if(bpb == -1):
        return -1

    json_str = bpb.get_json()
    resp = connect.send_msg(s, "SUBMIT_PACKAGE {}".format(json_str))
   
    if(resp == "INV_PKG_BUILD"):
        blog.error("Package submission rejected by server. The package build you attempted to submit is invalid.")
    elif(resp == "CMD_OK"):
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
# Cancel a job by id
#
def cancel_queued_job(s, job_id):
    resp = connect.send_msg(s, "CANCEL_QUEUED_JOB {}".format(job_id))
    
    if(resp == "INV_JOB_ID"):
        blog.error("No such job queued.")
        return

    if(resp == "JOB_CANCELED"):
        blog.info("Queued job {} cancelled.".format(job_id)) 

#
# Cancel all currently waiting jobs
#
def cancel_all_queued_jobs(s):
    resp = connect.send_msg(s, "CANCEL_ALL_QUEUED_JOBS")
    blog.info("Jobs canceled.") 

#
# Cancel 
#
def view_sys_log(s):
    resp = connect.send_msg(s, "VIEW_SYS_EVENTS")
    logs = json.loads(resp)
    
    if(len(logs) == 0):
        blog.info("No system events available.")
        return 0

    for l in logs:
        print(l)


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

#
# Get all dependers by package name
#
def view_dependers(s, pkg_name):
    resp = connect.send_msg(s, "GET_DEPENDERS {}".format(pkg_name))
    if(resp == "INV_PKG_NAME"):
        blog.error("No such packagebuild available.")
    else:
        blog.info("Available packagebuilds:")
        for b in json.loads(resp):
            print(b, end=", ")

        print()

#
# rebuild dependers (auto calc)
#
def rebuild_dependers(s, pkg_name):
    resp = connect.send_msg(s, "REBUILD_DEPENDERS {}".format(pkg_name))
    if(resp == "INV_PKG_NAME"):
        blog.error("No such package available.")
    elif(resp == "CIRCULAR_DEPENDENCY"):
        blog.error("Circular dependency detected. The requested batch build contains a circular dependency and could not be submitted.")
    elif(resp == "BATCH_QUEUED"):
        blog.info("Batch queued successfully.")

#
# difference between pkgs
#
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



#
# submit a branch solution to the masterserver as a batch (CROSS BUILD)
#
def submit_solution_cb(s, solution_file_str):
    submit_solution(s, solution_file_str, True) 

#
# submit a branch solution to the masterserver as a batch (RELEASE BUILD)
#
def submit_solution_rb(s, solution_file_str):
    submit_solution(s, solution_file_str, False) 

#
# submit a branch solution to the masterserver as a batch
#
def submit_solution(s, solution_file_str, use_crosstools):
    if(not os.path.exists(solution_file_str)):
        blog.error("Solution file not found.")
        return -1
    
    blog.info("Parsing solution..")
    solution_file = open(solution_file_str, "r")
    sl = solution_file.read().split("\n") 

    solution = [ ]

    for l in sl:
        if(len(l) == 0):
            break 

        if(l[0] != "#"):
            pkgs = [ ]
            split = l.strip().split(";")
            for sp in split:
                if(s != ""):
                    pkgs.append(sp)
            
            solution.append(pkgs)

    blog.info("Solution parsed!")
    blog.info("Submitting solution..")
    
    resp = ""

    if(use_crosstools):
        resp = connect.send_msg(s, "SUBMIT_SOLUTION_CB {}".format(json.dumps(solution)))
    else:
        resp = connect.send_msg(s, "SUBMIT_SOLUTION_RB {}".format(json.dumps(solution)))

    if(resp == "INV_SOL"):
        blog.error("Attempted to submit invalid solution.")
    elif(resp.split(" ")[0] == "PKG_BUILD_MISSING"):
        blog.error("A required package build is missing: {}".format(resp.split(" ")[1]))
    else:
        blog.info("Batch queued.")

#
# Checkout, edit and resubmit a package
#
def edit_pkgbuild(s, pkg_name):
    if(not "EDITOR" in os.environ):
        blog.error("No editor set.")
        return

    bpb_resp = connect.send_msg(s, "CHECKOUT_PACKAGE {}".format(pkg_name))
    
    # check if package is valid
    if(bpb_resp == "INV_PKG_NAME"):
        blog.error("The specified package could not be found.")
        return

    if(bpb_resp == "INV_PKG"):
        blog.error("The package build is damaged and could not be checked out.")
        return
    
    # get pkgbuild object from json
    pkgbuild = packagebuild.package_build.from_json(bpb_resp)

    timestamp = time.time()
    target_file = os.path.join("/tmp/", "tmp-edit-{}-{}".format(pkg_name, int(timestamp)))

    pkgbuild.write_build_file(target_file)
    blog.info("Successfully checkout out package {}".format(pkg_name))
    blog.info("Launching editor..")
    
    editor = os.environ["EDITOR"]
    os.system("{} {}".format(editor, target_file))


    if(not inpututil.ask_choice("Commit changes to remote?")):
        blog.error("Aborting.")
        os.remove(target_file) 
        return 

    # read new pkgbuild from changed file
    new_pkgbuild = packagebuild.package_build.from_file(target_file)
    if(not new_pkgbuild.is_valid()):
        blog.error("Local packagebuild validation failed. Aborting.")
        os.remove(target_file)
        return

    json_str = new_pkgbuild.get_json()
    resp = connect.send_msg(s, "SUBMIT_PACKAGE {}".format(json_str))
   
    if(resp == "INV_PKG_BUILD"):
        blog.error("Package submission rejected by server. The package build you attempted to submit is invalid.")
    elif(resp == "CMD_OK"):
        blog.info("Package submission accepted by server.")
    else:
        blog.error("An error occured: {}".format(resp))
    
    blog.info("Cleaning up..")
    os.remove(target_file)

def export(s, target_dir):
    managed_packagebuilds = json.loads(connect.send_msg(s, "MANAGED_PKGBUILDS"))
    blog.info("Checking out {} pkgbuilds..".format(len(managed_packagebuilds)))
 
    if(os.path.exists(target_dir) and os.path.isdir(target_dir)):
        blog.error("Target directory {} already exists.".format(target_dir))
        return

    pkgbuilds = [ ]

    for pkgbuild_name in managed_packagebuilds:
        blog.info("Checking out: {}".format(pkgbuild_name))
        resp = connect.send_msg(s, "CHECKOUT_PACKAGE {}".format(pkgbuild_name))
        
        # check if package is valid
        if(resp == "INV_PKG_NAME"):
            blog.error("Packagebuild {} could not be found.".format(pkgbuild_name))
            return

        if(resp == "INV_PKG"):
            blog.error("Packagebuild {} is damaged and could not be checked out.".format(pkgbuild_name))
            return
        
        pkgbuilds.append(packagebuild.package_build.from_json(resp))
   
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


def _import(s, target_dir):
    bpb_files = []
    for root, dirs, files in os.walk(target_dir):
        for file in files:
            if file.endswith(".bpb"):
                bpb_files.append(os.path.abspath(os.path.join(root, file)))    
    
    blog.info("Found {} package files to import.".format(len(bpb_files)))
    if(not inpututil.ask_choice("Submit packages?")):
        blog.error("Aborting.")
        return

    for path in bpb_files:
        bpb = packagebuild.package_build.from_file(path)
        
        if(bpb == -1):
            blog.error("Could not load packagebuild file: {}".format(path))
            return -1
         
        resp = connect.send_msg(s, "SUBMIT_PACKAGE {}".format(bpb.get_json()))
    
    blog.info("Import completed.")

def get_client_info(s, client_name):
    resp = connect.send_msg(s, "GET_CLIENT_INFO {}".format(client_name))
    
    if(resp == "INV_CLIENT_NAME"):
        blog.error("No such client found.")
        return

    client_info = json.loads(resp)
    
    print()
    print("Client information - {}".format(client_name))
    print()
    for attr in client_info:
        print("{}: {}".format(attr, client_info[attr]))
