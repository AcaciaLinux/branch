import main
import json
import os
import blog
import packagebuild
import time

from branchpacket import BranchResponse, BranchRequest, BranchStatus
from utils import inpututil

#
# checkout package
#
def checkout_package(bc, pkg_name):
    """
    Checks out a package using the given BranchClient

    :param bc: BranchClient
    :param pkg_name: Name of the package to checkout
    """
    
    checkout_response: BranchResponse = bc.send_recv_msg(BranchRequest("CHECKOUT", pkg_name))
        
    match checkout_response.statuscode:

        case BranchStatus.OK:
            blog.info("Received packagebuild from server.")
            pkgbuild = packagebuild.package_build.from_dict(checkout_response.payload)
            target_file = os.path.join(pkg_name, "package.bpb")
            
            if(not os.path.exists(pkg_name)):
                os.mkdir(pkg_name)

            if(os.path.exists(target_file)):
                if(not inpututil.ask_choice("Checking out will overwrite your local working copy. Continue?")):
                    blog.error("Aborting.")
                    return
            
            pkgbuild.write_build_file(target_file)
            blog.info("Successfully checked out package '{}'.".format(pkg_name))
            return

        case BranchStatus.REQUEST_FAILURE:
            blog.error("Server: {}".format(checkout_response.payload))
            return
        
        case other:
            blog.error("Unhandled response.")
            return
   
def submit_package(bc):
    """
    Submit 'package.bpb' from the current working directory
    to the server.

    :param bc: BranchClient
    :param pkg_name: Packagebuild name
    """

    pkgbuild = packagebuild.package_build.from_file("package.bpb")
    if(not pkgbuild.is_valid()):
        blog.error("Local packagebuild validation failed. Packagebuild is invalid")
        return

    submit_response: BranchResponse = bc.send_recv_msg(BranchRequest("SUBMIT", pkgbuild.get_dict()))

    match submit_response.statuscode:

        case BranchStatus.OK:
            blog.info("Packagebuild submission accepted by server.")
            return

        case BranchStatus.REQUEST_FAILURE:
            blog.error("Packagebuild submission rejected by server. The packagebuild you attempted to submit is invalid")
            return

        case other:
            blog.error("Server: {}".format(submit_response.payload))
            return

#
# Request a release build from a specified package
#
def release_build(bc, pkg_name):
    """
    Request a releasebuild from the server.

    :param bc: BranchClient
    :param pkg_name: Packagebuild name
    """

    releasebuild_response: BranchResponse = bc.send_recv_msg(BranchRequest("BUILD", {
            "pkgname": pkg_name,
            "buildtype": "RELEASE"
        }))
    
    match releasebuild_response.statuscode:

        case BranchStatus.OK:
            blog.info("Server: {}".format(releasebuild_response.payload))
            return

        case BranchStatus.REQUEST_FAILURE:
            blog.error("Server: {}".format(releasebuild_response.payload))
            return

        case other:
            blog.error("Server: {}".format(releasebuild_response.payload))
            return

def cross_build(bc, pkg_name):
    """
    Request a releasebuild from the server.

    :param bc: BranchClient
    :param pkg_name: Packagebuild name
    """

    releasebuild_response: BranchResponse = bc.send_recv_msg(BranchRequest("BUILD", {
            "pkgname": pkg_name,
            "buildtype": "CROSS"
        }))
    
    match releasebuild_response.statuscode:

        case BranchStatus.OK:
            blog.info("Server: {}".format(releasebuild_response.payload))
            return

        case BranchStatus.REQUEST_FAILURE:
            blog.error("Server: {}".format(releasebuild_response.payload))
            return

        case other:
            blog.error("Server: {}".format(releasebuild_response.payload))
            return

def build_status(bc):
    """
    Request build_status from the server.

    :param bc: BranchClient
    """
    status_response = bc.send_recv_msg(BranchRequest("GETJOBSTATUS", ""))

    match status_response.statuscode:
        case BranchStatus.OK:
            queued_jobs = status_response.payload["queuedjobs"]
            running_jobs = status_response.payload["runningjobs"]
            completed_jobs = status_response.payload["completedjobs"]
            
            if(not completed_jobs and not running_jobs and not queued_jobs):
                blog.info("No jobs.")

            if(queued_jobs):
                print()
                print("QUEUED JOBS:")
                print ("{:<20} {:<15} {:<40} {:<10}".format("NAME", "STATUS", "ID", "REQUESTED BY"))

                for job in queued_jobs:
                    print ("{:<20} {:<15} {:<40} {:<10}".format(job['job_name'], job['job_status'], job['job_id'], job['requesting_client']))
            
            if(running_jobs):
                print()
                print("RUNNING JOBS:")
                print ("{:<20} {:<15} {:<40} {:<10}".format("NAME", "STATUS", "ID", "REQUESTED BY"))

                for job in running_jobs:
                    print ("{:<20} {:<15} {:<40} {:<10}".format(job['job_name'], job['job_status'], job['job_id'], job['requesting_client']))

            if(completed_jobs):
                print()
                print("COMPLETED JOBS:")
                print ("{:<20} {:<15} {:<40} {:<10}".format("NAME", "STATUS", "ID", "REQUESTED BY"))

                for job in completed_jobs:
                    if(job['job_status'] == "FAILED"):
                        print ("{:<20} \033[91m{:<15}\033[0m {:<40} {:<10}".format(job['job_name'], job['job_status'], job['job_id'], job['requesting_client']))
                    else:
                        print ("{:<20} \033[92m{:<15}\033[0m {:<40} {:<10}".format(job['job_name'], job['job_status'], job['job_id'], job['requesting_client']))

        case other:
            blog.error("Server: {}".format(status_response.payload))

def client_status(bc):
    """
    Request client_status from the server.

    :param bc: BranchClient
    """
    clientstatus_response: BranchResponse = bc.send_recv_msg(BranchRequest("GETCONNECTEDCLIENTS", ""))

    controllers = clientstatus_response.payload["controllers"]
    buildbots = clientstatus_response.payload["buildbots"]
    print()

    print("CONTROLLER CLIENT ({}):".format(len(controllers)))
    for name in controllers:
        print(name, end=' ')
    print()

    print()
    print()

    print("BUILDBOT CLIENTS ({}):".format(len(buildbots)))
    for name in buildbots:
        print(name, end=' ')
    print()

def cancel_queued_job(bc, job_id):
    """
    Cancel a queued job on the server

    :param bc: BranchClient
    :param job_id: The jobs id
    """
    cancelqueuedjob_response: BranchResponse = bc.send_recv_msg(BranchRequest("CANCELQUEUEDJOB", job_id)) 
    
    match cancelqueuedjob_response.statuscode:
        case BranchStatus.OK:
            blog.info("Server: {}".format(cancelqueuedjob_response.payload))
            return

        case other:
            blog.error("Server: {}".format(cancelqueuedjob_response.payload))
            return

def cancel_all_queued_jobs(bc):
    """
    Cancel all queued jobs on the server.
    
    :param bc: BranchClient
    """
    cancelall_response: BranchResponse = bc.send_recv_msg(BranchRequest("CANCELQUEUEDJOBS", ""))
    
    match cancelall_response.statuscode:
        case BranchStatus.OK:
            blog.info("Server: {}".format(cancelall_response.payload))
            return

        case other:
            blog.error("Server: {}".format(cancelall_response.payload))
            return

#
# View system logs 
#
def view_sys_log(bc):
    """
    View the syslog

    :param bc: BranchClient
    """
    syslog_response: BranchResponse = bc.send_recv_msg(BranchRequest("GETSYSLOG", ""))
    
    match syslog_response.statuscode:
        case BranchStatus.OK:
            if(len(syslog_response.payload) == 0):
                blog.info("No system events available")
                return
            
            print("SYSLOG: ")
            for line in syslog_response.payload:
                print(line)

        case other:
            blog.error("Server: {}".format(cancelall_response.payload))
            return

#
# get build log
#
def get_buildlog(bc, job_id):
    """
    Get a jobs buildlog
    
    :param bc: BranchClient
    :param job_id: job_id
    """
    joblog_response: BranchResponse = bc.send_recv_msg(Branchrequest("GETJOBLOG", job_id))
    
    match joblog_response.statuscode:
        case BranchStatus.OK:
            print("\nBUILD LOG FOR '{}':\n".format(job_id))
            for line in joblog_response.payload:
                print(line)

        case BranchStatus.REQUEST_FAILURE:
            blog.error("Server: {}".format(joblog_response.payload))

        case other:
            blog.error("Server: {}".format(joblog_response.payload))
    
  


def clear_completed_jobs(bc):
    """
    Clears all completed jobs

    :param bc: BranchClient
    """
    clearcompleted_response = bc.send_recv_msg(BranchRequest("CLEARCOMPLETEDJOBS", ""))

    match clearcompleted_response.statuscode:
        case BranchStatus.OK:
            blog.info("Server: {}".format(clearcompleted_response.payload))
            return

        case other:
            blog.error("Server: {}".format(clearcompleted_response.payload))
            return

def get_managed_packages(bc):
    """
    Get managed packages

    :param bc: BranchClient
    """
    managedpkgs_response: BranchRequest = bc.send_recv_msg(BranchRequest("GETMANAGEDPKGS", ""))

    match managedpkgs_response.statuscode:
        case BranchStatus.OK:
            print("Managed packages:")
            print()

            for count, item in enumerate(sorted(managedpkgs_response.payload), 1):
                print(item.ljust(30), end="")
                if(count % 4 == 0):
                   print()

            print()
            return

        case other:
            blog.error("Server: {}".format(managedpkgs_response.payload))
            return

def get_managed_pkgbuilds(bc):
    """
    Get managed packagebuilds

    :param bc: BranchClient
    """
    managedpkgs_response: BranchResponse = bc.send_recv_msg(BranchRequest("GETMANAGEDPKGBUILDS", ""))

    match managedpkgs_response.statuscode:
        case BranchStatus.OK:
            print("Managed packagebuilds:")
            print()

            for count, item in enumerate(sorted(managedpkgs_response.payload), 1):
                print(item.ljust(30), end="")
                if(count % 4 == 0):
                   print()

            print()
            return

        case other:
            blog.error("Server: {}".format(managedpkgs_response.payload))
            return

#
# Get all dependers by package name
#
def view_dependers(bc, pkg_name: str):
    """
    View all dependers of a specified packagebuild

    :param bc: BranchClient
    :param pkg_name: pkg_name
    """
    viewdependers_response: BranchResponse = bc.send_recv_msg(BranchRequest("GETDEPENDERS", pkg_name))

    match viewdependers_response.statuscode:

        case BranchStatus.OK:
            blog.info("Dependencies for {}:".format(pkg_name))
            
            print(viewdependers_response.payload)

            amount_release_build = len(viewdependers_response.payload["releasebuild"])
            amount_cross_build = len(viewdependers_response.payload["crossbuild"])
             
            list_len = 0

            if(amount_cross_build > amount_release_build):
                list_len = amount_cross_build
            else:
                list_len = amount_release_build
            
            print("{:<40} {:<40}".format("RELEASE BUILD", "CROSS BUILD"))
            print()

            for i in range(list_len):
                rb_name = ""
                cb_name = ""

                if(i < amount_release_build):
                    rb_name = viewdependers_response.payload["releasebuild"][i]
                
                if(i < amount_cross_build):
                    cb_name = viewdependers_response.payload["crossbuild"][i]

                print ("{:<40} {:<40}".format(rb_name, cb_name))

            print()

        case BranchStatus.REQUEST_FAILURE:
            blog.error("Server: {}".format(viewdependers_response.payload))
            return

        case other:
            blog.error("Server: {}".format(viewdependers_response.payload))
            return

def rebuild_dependers(bc, pkg_name: str):
    """
    Rebuild all packages that depend on the specified package

    :param bc: BranchClient
    :param pkg_name: Name of package
    """
    start_time = int(time.time_ns() / 1000000000)

    blog.info("Calculating dependers.. This may take a few moments")
    rebuild_dependers_response: BranchResponse = bc.send_recv_msg(BranchRequest("REBUILDDEPENDERS", pkg_name))
    
    end_time = int(time.time_ns() / 1000000000)

    match rebuild_dependers_response.statuscode:
        case BranchStatus.OK:
            blog.info("Server: {}".format(rebuild_dependers_response.payload))
            return

        case other:
            blog.error("Server: {}".format(rebuild_dependers_response.payload))
            return

def get_diff_pkg(bc):
    """
    Print the difference between available packagebuilds and their package
    counterparts

    :param bc: BranchClient
    """
    managedpkgs_response: BranchRequest = bc.send_recv_msg(BranchRequest("GETMANAGEDPKGS", ""))
    managedpkgbuilds_response: BranchRequest = bc.send_recv_msg(BranchRequest("GETMANAGEDPKGBUILDS", ""))

    if(managedpkgs_response.statuscode == BranchStatus.OK and managedpkgbuilds_response.statuscode == BranchStatus.OK):
        print("Difference between package and packagebuilds:\n")
        for count, item in enumerate(sorted(managedpkgbuilds_response.payload), 1):

            if(item in managedpkgs_response.payload):
                print('\033[92m', end="")
            else:
                print('\033[91m', end="")

            print(item.ljust(30), end="")
            print('\033[0m', end="")
            if(count % 4 == 0):
               print()

        print()
    else:
        blog.error("Could not fetch difference.")

def submit_solution_cb(bc, solution_file_str: str):
    """
    Submit a solution to the server

    :param bc: BranchClient
    :param solution_file_str: Path to the solution file
    """
    submit_solution(bc, solution_file_str, True) 

def submit_solution_rb(bc, solution_file_str):
    """
    Submit a solution to the server

    :param bc: BranchClient
    :param solution_file_str: Path to the solution file
    """
    submit_solution(bc, solution_file_str, False) 

#
# submit a branch solution to the masterserver as a batch
#
def submit_solution(bc, solution_file_str, use_crosstools):
    """
    Submit a solution to the server

    :param bc: BranchClient
    :param solution_file_str: Path to the solution file
    :param use_crosstools: Build in 'CROSS' or 'RELEASE' mode.
    """
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
                if(sp != ""):
                    pkgs.append(sp)
            
            solution.append(pkgs)
    

    if(use_crosstools):
        blog.info("Submitting solution with buildtype 'CROSS'..")
        solution_response: BranchResponse = bc.send_recv_msg(BranchRequest("SUBMITSOLUTION", {
            "solution": solution,
            "buildtype": "CROSS"
        }))
    else:
        blog.info("Submitting solution with buildtype 'RELEASE'..")
        solution_response: BranchResponse = bc.send_recv_msg(BranchRequest("SUBMITSOLUTION", {
            "solution": solution,
            "buildtype": "RELEASE"
        }))
    
    match solution_response.statuscode:

        case BranchStatus.OK:
            blog.info("Server: {}".format(solution_response.payload))
            return
        
        case other:
            blog.error("Server: {}".format(solution_response.payload))
            return

def edit_pkgbuild(bc, pkg_name):
    """
    Checkout, edit and resubmit a given packagebuild

    :param bc: BranchClient
    :param pkg_name: Name of packagebuild to edit
    """
    if(not "EDITOR" in os.environ):
        blog.error("No editor set.")
        return

    checkout_response: BranchResponse = bc.send_recv_msg(BranchRequest("CHECKOUT", pkg_name))
    
    match checkout_response.statuscode:

        case BranchStatus.OK:
            pkgbuild = packagebuild.package_build.from_dict(checkout_response.payload)
   
        case other:
            blog.error("Server: {}".format(checkout_response.payload))
            return

    target_file = os.path.join("/tmp/", "tmp-edit-{}-{}".format(pkg_name, int(time.time())))

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

    submit_response: BranchResponse = bc.send_recv_msg(BranchRequest("SUBMIT", new_pkgbuild.get_dict()))

    match submit_response.statuscode:

        case BranchStatus.OK:
            blog.info("Packagebuild edited.")

        case other:
            blog.error("Server: {}".format(submit_response.payload))
   
    blog.info("Cleaning up..")
    os.remove(target_file)

#
# export all packagebuilds to a 
#
def export(bc, target_dir):
    """
    Export all package builds on the server to a directroy
    
    :param bc: BranchClient
    :param target_dir: Target directory
    """
    if(os.path.exists(target_dir) and os.path.isdir(target_dir)):
        blog.error("Target directory {} already exists.".format(target_dir))
        return

    managed_packagebuilds_response: BranchRequest = bc.send_recv_msg(BranchRequest("GETMANAGEDPKGBUILDS", ""))
    
    match managed_packagebuilds_response.statuscode:
        case BranchStatus.OK:
            managed_packagebuilds = managed_packagebuilds_response.payload

        case other:
            blog.error("Server: {}".format(managed_packagebuilds_response.payload))
            return

    blog.info("Checking out {} pkgbuilds..".format(len(managed_packagebuilds)))
 
    pkgbuilds = [ ]

    for pkgbuild_name in managed_packagebuilds:
        checkout_response: BranchResponse = bc.send_recv_msg(BranchRequest("CHECKOUT", pkgbuild_name))

        match checkout_response.statuscode:

            case BranchStatus.OK:
                blog.info("Checked out packagebuild: '{}'".format(pkgbuild_name))
                pkgbuilds.append(packagebuild.package_build.from_dict(checkout_response.payload))
            
            case other:
                blog.error("Packagebuild '{}' is damaged. Server: {}".format(pkgbuild_name, checkout_response.payload))
        
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


def _import(bc, target_dir):
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
        pkgbuild = packagebuild.package_build.from_file(path)
        
        if(not pkgbuild.is_valid()):
            blog.error("File is not a valid packagebuild. Skipped: {}".format(bpb_files))
            continue
        
        submit_response: BranchResponse = bc.send_recv_msg(BranchRequest("SUBMIT", pkgbuild.get_dict()))
        
        match submit_response.statuscode:

            case BranchStatus.OK:
                blog.info("Package build imported: {}".format(pkgbuild.name))

            case other:
                blog.error("Failed to import {}. Server: {}".format(pkgbuild.name, submit_response.payload))


    blog.info("Import completed.")

def get_client_info(bc, client_name):
    clientinfo_request: BranchResponse = bc.send_recv_msg(BranchRequest("GETCLIENTINFO", client_name))
    
    
    print(clientinfo_request.payload)



    if(resp == "INV_CLIENT_NAME"):
        blog.error("No such client found.")
        return

    client_info = json.loads(resp)
    
    print()
    print("Client information - {}".format(client_name))
    print()
    for attr in client_info:
        print("{}: {}".format(attr, client_info[attr]))

def transfer_extra_source(bc, file_path):
    blog.info("Loading extra source..")

    file_name = os.path.basename(file_path)
    blog.info("Will commit as filename: {}".format(file_name))

    byte_count = os.path.getsize(file_path)
    
    blog.info("Enter a description: ")
    description = input()

    info_dict = {
        "description": description,
        "filename": file_name,
        "filelen": byte_count
    }

    resp = bc.send_recv_msg("TRANSFER_EXTRA_SOURCE {}".format(json.dumps(info_dict)))

    if(not resp == "CMD_OK"):
        blog.error("Could not switch to file transfer mode.")
        return

    blog.info("File transfer setup completed.")
    blog.info("Sending file..")
    bc.send_file(file_path)
    
    resp = bc.send_recv_msg("COMPLETE_TRANSFER")

    if(not resp == "CMD_OK"):
        blog.error("Received error response from server: {}".format(resp))
    else:
        blog.info("File transfer completed.")

def view_extra_sources(bc):
    blog.info("Fetching available extra sources.")

    resp = json.loads(bc.send_recv_msg("GET_MANAGED_EXTRA_SOURCES"))
    print ("\n\n{:<40} {:<50} {:<40}".format("ID", "FILENAME", "DESCRIPTION"))

    for es in resp:
        print ("{:<40} {:<50} {:<40}".format(es["id"], es["filename"], es["description"]))


def remove_extra_source(bc, es_id):
    resp = bc.send_recv_msg("REMOVE_EXTRA_SOURCE {}".format(es_id))

    if(resp == "CMD_OK"):
        blog.info("Extra source deleted.")
    else:
        blog.error("Could not delete extra source.")
