import time
import os
import blog
import packagebuild

from branchpacket import BranchResponse, BranchRequest, BranchStatus
from utils import inpututil


def checkout_package(bc, pkg_name):
    """
    Checks out a package using the given BranchClient

    :param bc: BranchClient
    :param pkg_name: Name of the package to checkout
    """

    checkout_response: BranchResponse = bc.send_recv_msg(
        BranchRequest("CHECKOUT", pkg_name))

    match checkout_response.statuscode:

        case BranchStatus.OK:
            blog.info("Received packagebuild from server.")
            pkgbuild = packagebuild.package_build.from_dict(
                checkout_response.payload)
            target_file = os.path.join(pkg_name, "package.bpb")

            if (not os.path.exists(pkg_name)):
                os.mkdir(pkg_name)

            if (os.path.exists(target_file)):
                if (not inpututil.ask_choice("Checking out will overwrite your local working copy. Continue?")):
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
    if (not pkgbuild.is_valid()):
        blog.error(
            "Local packagebuild validation failed. Packagebuild is invalid")
        return

    submit_response: BranchResponse = bc.send_recv_msg(
        BranchRequest("SUBMIT", pkgbuild.get_dict()))

    match submit_response.statuscode:

        case BranchStatus.OK:
            blog.info("Packagebuild submission accepted by server.")
            return

        case BranchStatus.REQUEST_FAILURE:
            blog.error(
                "Packagebuild submission rejected by server. The packagebuild you attempted to submit is invalid")
            return

        case other:
            blog.error(f"Server: {submit_response.payload}")
            return


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
            blog.info(f"Server: {releasebuild_response.payload}")
            return

        case BranchStatus.REQUEST_FAILURE:
            blog.error(f"Server: {releasebuild_response.payload}")
            return

        case other:
            blog.error(f"Server: {releasebuild_response.payload}")
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
            blog.info(f"Server: {releasebuild_response.payload}")
            return

        case other:
            blog.error(f"Server: {releasebuild_response.payload}")
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

            if (not completed_jobs and not running_jobs and not queued_jobs):
                blog.info("No jobs.")

            if (queued_jobs):
                print()
                print("QUEUED JOBS:")
                print("{:<20} {:<15} {:<40} {:<10}".format(
                    "NAME", "STATUS", "ID", "REQUESTED BY"))

                for job in queued_jobs:
                    print("{:<20} {:<15} {:<40} {:<10}".format(
                        job['job_name'], job['job_status'], job['job_id'], job['requesting_client']))

            if (running_jobs):
                print()
                print("RUNNING JOBS:")
                print("{:<20} {:<15} {:<40} {:<10}".format(
                    "NAME", "STATUS", "ID", "REQUESTED BY"))

                for job in running_jobs:
                    print("{:<20} {:<15} {:<40} {:<10}".format(
                        job['job_name'], job['job_status'], job['job_id'], job['requesting_client']))

            if (completed_jobs):
                print()
                print("COMPLETED JOBS:")
                print("{:<20} {:<15} {:<40} {:<10}".format(
                    "NAME", "STATUS", "ID", "REQUESTED BY"))

                for job in completed_jobs:
                    if (job['job_status'] == "FAILED"):
                        print("{:<20} \033[91m{:<15}\033[0m {:<40} {:<10}".format(
                            job['job_name'], job['job_status'], job['job_id'], job['requesting_client']))
                    else:
                        print("{:<20} \033[92m{:<15}\033[0m {:<40} {:<10}".format(
                            job['job_name'], job['job_status'], job['job_id'], job['requesting_client']))

        case other:
            blog.error(f"Server: {status_response.payload}")


def client_status(bc):
    """
    Request client_status from the server.

    :param bc: BranchClient
    """
    clientstatus_response: BranchResponse = bc.send_recv_msg(
        BranchRequest("GETCONNECTEDCLIENTS", ""))

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
    cancelqueuedjob_response: BranchResponse = bc.send_recv_msg(
        BranchRequest("CANCELQUEUEDJOB", job_id))

    match cancelqueuedjob_response.statuscode:
        case BranchStatus.OK:
            blog.info(f"Server: {cancelqueuedjob_response.payload}")
            return

        case other:
            blog.error(f"Server: {cancelqueuedjob_response.payload}")
            return


def cancel_all_queued_jobs(bc):
    """
    Cancel all queued jobs on the server.

    :param bc: BranchClient
    """
    cancelall_response: BranchResponse = bc.send_recv_msg(
        BranchRequest("CANCELQUEUEDJOBS", ""))

    match cancelall_response.statuscode:
        case BranchStatus.OK:
            blog.info(f"Server: {cancelall_response.payload}")
            return

        case other:
            blog.error(f"Server: {cancelall_response.payload}")
            return


def view_sys_log(bc):
    """
    View the syslog

    :param bc: BranchClient
    """
    syslog_response: BranchResponse = bc.send_recv_msg(
        BranchRequest("GETSYSLOG", ""))

    match syslog_response.statuscode:
        case BranchStatus.OK:
            if (len(syslog_response.payload) == 0):
                blog.info("No system events available")
                return

            print("SYSLOG: ")
            for line in syslog_response.payload:
                print(line)

        case other:
            blog.error(f"Server: {syslog_response.payload}")
            return


def get_buildlog(bc, job_id):
    """
    Get a jobs buildlog

    :param bc: BranchClient
    :param job_id: job_id
    """
    joblog_response: BranchResponse = bc.send_recv_msg(
        BranchRequest("GETJOBLOG", job_id))

    match joblog_response.statuscode:
        case BranchStatus.OK:
            print("\nBUILD LOG FOR '{}':\n".format(job_id))
            for line in joblog_response.payload:
                print(line)

        case other:
            blog.error(f"Server: {joblog_response.payload}")


def clear_completed_jobs(bc):
    """
    Clears all completed jobs

    :param bc: BranchClient
    """
    clearcompleted_response = bc.send_recv_msg(
        BranchRequest("CLEARCOMPLETEDJOBS", ""))

    match clearcompleted_response.statuscode:
        case BranchStatus.OK:
            blog.info(f"Server: {clearcompleted_response.payload}")
            return

        case other:
            blog.error(f"Server: {clearcompleted_response.payload}")
            return


def get_managed_packages(bc):
    """
    Get managed packages

    :param bc: BranchClient
    """
    managedpkgs_response: BranchRequest = bc.send_recv_msg(
        BranchRequest("GETMANAGEDPKGS", ""))

    match managedpkgs_response.statuscode:
        case BranchStatus.OK:
            print("Managed packages:")
            print()

            for count, item in enumerate(sorted(managedpkgs_response.payload), 1):
                print(item.ljust(30), end="")
                if (count % 4 == 0):
                    print()

            print()
            return

        case other:
            blog.error(f"Server: {managedpkgs_response.payload}")
            return


def get_managed_pkgbuilds(bc):
    """
    Get managed packagebuilds

    :param bc: BranchClient
    """
    managedpkgs_response: BranchResponse = bc.send_recv_msg(
        BranchRequest("GETMANAGEDPKGBUILDS", ""))

    match managedpkgs_response.statuscode:
        case BranchStatus.OK:
            print("Managed packagebuilds:")
            print()

            for count, item in enumerate(sorted(managedpkgs_response.payload), 1):
                print(item.ljust(30), end="")
                if (count % 4 == 0):
                    print()

            print()
            return

        case other:
            blog.error(f"Server: {managedpkgs_response.payload}")
            return


def view_dependers(bc, pkg_name: str):
    """
    View all dependers of a specified packagebuild

    :param bc: BranchClient
    :param pkg_name: pkg_name
    """
    viewdependers_response: BranchResponse = bc.send_recv_msg(
        BranchRequest("GETDEPENDERS", pkg_name))

    match viewdependers_response.statuscode:

        case BranchStatus.OK:
            blog.info("Dependencies for {}:".format(pkg_name))

            print(viewdependers_response.payload)

            amount_release_build = len(
                viewdependers_response.payload["releasebuild"])
            amount_cross_build = len(
                viewdependers_response.payload["crossbuild"])

            list_len = 0

            if (amount_cross_build > amount_release_build):
                list_len = amount_cross_build
            else:
                list_len = amount_release_build

            print("{:<40} {:<40}".format("RELEASE BUILD", "CROSS BUILD"))
            print()

            for i in range(list_len):
                rb_name = ""
                cb_name = ""

                if (i < amount_release_build):
                    rb_name = viewdependers_response.payload["releasebuild"][i]

                if (i < amount_cross_build):
                    cb_name = viewdependers_response.payload["crossbuild"][i]

                print("{:<40} {:<40}".format(rb_name, cb_name))

            print()

        case other:
            blog.error(f"Server: {viewdependers_response.payload}")
            return


def rebuild_dependers(bc, pkg_name: str):
    """
    Rebuild all packages that depend on the specified package

    :param bc: BranchClient
    :param pkg_name: Name of package
    """
    start_time = int(time.time_ns() / 1000000000)

    blog.info("Calculating dependers.. This may take a few moments")
    rebuild_dependers_response: BranchResponse = bc.send_recv_msg(
        BranchRequest("REBUILDDEPENDERS", pkg_name))

    end_time = int(time.time_ns() / 1000000000)

    match rebuild_dependers_response.statuscode:
        case BranchStatus.OK:
            blog.info(f"Server: {rebuild_dependers_response.payload}")
            return

        case other:
            blog.error(f"Server: {rebuild_dependers_response.payload}")
            return


def get_diff_pkg(bc):
    """
    Print the difference between available packagebuilds and their package
    counterparts

    :param bc: BranchClient
    """
    managedpkgs_response: BranchRequest = bc.send_recv_msg(
        BranchRequest("GETMANAGEDPKGS", ""))
    managedpkgbuilds_response: BranchRequest = bc.send_recv_msg(
        BranchRequest("GETMANAGEDPKGBUILDS", ""))

    if (managedpkgs_response.statuscode == BranchStatus.OK and managedpkgbuilds_response.statuscode == BranchStatus.OK):
        print("Difference between package and packagebuilds:\n")
        for count, item in enumerate(sorted(managedpkgbuilds_response.payload), 1):

            if (item in managedpkgs_response.payload):
                print('\033[92m', end="")
            else:
                print('\033[91m', end="")

            print(item.ljust(30), end="")
            print('\033[0m', end="")
            if (count % 4 == 0):
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


def submit_solution(bc, solution_file_str, use_crosstools):
    """
    Submit a solution to the server

    :param bc: BranchClient
    :param solution_file_str: Path to the solution file
    :param use_crosstools: Build in 'CROSS' or 'RELEASE' mode.
    """
    if (not os.path.exists(solution_file_str)):
        blog.error("Solution file not found.")
        return -1

    blog.info("Parsing solution..")
    solution_file = open(solution_file_str, "r")
    sl = solution_file.read().split("\n")

    solution = []

    for l in sl:
        if (len(l) == 0):
            break

        if (l[0] != "#"):
            pkgs = []
            split = l.strip().split(";")
            for sp in split:
                if (sp != ""):
                    pkgs.append(sp)

            solution.append(pkgs)

    if (use_crosstools):
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
            blog.info(f"Server: {solution_response.payload}")
            return

        case other:
            blog.error(f"Server: {solution_response.payload}")
            return


def edit_pkgbuild(bc, pkg_name):
    """
    Checkout, edit and resubmit a given packagebuild

    :param bc: BranchClient
    :param pkg_name: Name of packagebuild to edit
    """
    if (not "EDITOR" in os.environ):
        blog.error("No editor set.")
        return

    checkout_response: BranchResponse = bc.send_recv_msg(
        BranchRequest("CHECKOUT", pkg_name))

    match checkout_response.statuscode:

        case BranchStatus.OK:
            pkgbuild = packagebuild.package_build.from_dict(
                checkout_response.payload)

        case other:
            blog.error("Server: {}".format(checkout_response.payload))
            return

    target_file = os.path.join(
        "/tmp/", "tmp-edit-{}-{}".format(pkg_name, int(time.time())))

    pkgbuild.write_build_file(target_file)
    blog.info("Successfully checkout out package {}".format(pkg_name))
    blog.info("Launching editor..")

    editor = os.environ["EDITOR"]
    os.system("{} {}".format(editor, target_file))

    if (not inpututil.ask_choice("Commit changes to remote?")):
        blog.error("Aborting.")
        os.remove(target_file)
        return

    # read new pkgbuild from changed file
    new_pkgbuild = packagebuild.package_build.from_file(target_file)
    if (not new_pkgbuild.is_valid()):
        blog.error("Local packagebuild validation failed. Aborting.")
        os.remove(target_file)
        return

    submit_response: BranchResponse = bc.send_recv_msg(
        BranchRequest("SUBMIT", new_pkgbuild.get_dict()))

    match submit_response.statuscode:

        case BranchStatus.OK:
            blog.info("Packagebuild edited.")

        case other:
            blog.error(f"Server: {submit_response.payload}")

    blog.info("Cleaning up..")
    os.remove(target_file)


def export(bc, target_dir):
    """
    Export all package builds on the server to a directroy

    :param bc: BranchClient
    :param target_dir: Target directory
    """
    if (os.path.exists(target_dir) and os.path.isdir(target_dir)):
        blog.error(f"Target directory {target_dir} already exists.")
        return

    managed_packagebuilds_response: BranchRequest = bc.send_recv_msg(
        BranchRequest("GETMANAGEDPKGBUILDS", ""))

    match managed_packagebuilds_response.statuscode:
        case BranchStatus.OK:
            managed_packagebuilds = managed_packagebuilds_response.payload

        case other:
            blog.error(f"Server: {managed_packagebuilds_response.payload}")
            return

    blog.info("Checking out {} pkgbuilds..".format(len(managed_packagebuilds)))

    pkgbuilds = []

    for pkgbuild_name in managed_packagebuilds:
        checkout_response: BranchResponse = bc.send_recv_msg(
            BranchRequest("CHECKOUT", pkgbuild_name))

        match checkout_response.statuscode:

            case BranchStatus.OK:
                blog.info(f"Checked out packagebuild: '{pkgbuild_name}'")
                pkgbuilds.append(packagebuild.package_build.from_dict(checkout_response.payload))

            case other:
                blog.error(f"Packagebuild '{pkgbuild_name}' is damaged. Server: {checkout_response.payload}")

    blog.info(f"Saving packagebuilds to {target_dir}")
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


def _import(bc, target_dir: str):
    """
    Import any .bpb file in a given packagebuild directory
    """
    bpb_files = []
    for root, dirs, files in os.walk(target_dir):
        for file in files:
            if file.endswith(".bpb"):
                bpb_files.append(os.path.abspath(os.path.join(root, file)))

    blog.info("Found {} package files to import.".format(len(bpb_files)))
    if (not inpututil.ask_choice("Submit packages?")):
        blog.error("Aborting.")
        return

    for path in bpb_files:
        pkgbuild = packagebuild.package_build.from_file(path)

        if (not pkgbuild.is_valid()):
            blog.error(f"File is not a valid packagebuild. Skipped: {path}")
            continue

        submit_response: BranchResponse = bc.send_recv_msg(
            BranchRequest("SUBMIT", pkgbuild.get_dict()))

        match submit_response.statuscode:

            case BranchStatus.OK:
                blog.info(f"Package build imported: {pkgbuild.name}")

            case other:
                blog.error(f"Failed to import {pkgbuild.name}. Server: {submit_response.payload}")

    blog.info("Import completed.")


def get_client_info(bc, client_name: str):
    """
    Get client information by name

    :param bc: BranchClient
    :param client_name: client_name as str
    """
    clientinfo_request: BranchResponse = bc.send_recv_msg(
        BranchRequest("GETCLIENTINFO", client_name))

    print()
    print("Client information - {}".format(client_name))
    print()
    for attr in clientinfo_request.payload:
        print("{}: {}".format(attr, clientinfo_request.payload[attr]))


def transfer_extra_source(bc, file_path):
    """
    Setup an extra source transfer with the server

    :param bc: BranchClient
    :param file_path: Path to file
    """
    if (not os.path.exists(file_path)):
        blog.error("No such file or directory.")
        return

    blog.info("Loading extra source..")

    file_name = os.path.basename(file_path)
    blog.info(f"Will commit as filename: {filename}")

    byte_count = os.path.getsize(file_path)

    blog.info("Enter a description: ")
    description = input()

    info_dict = {
        "filedescription": description,
        "filename": file_name,
        "filelength": byte_count
    }

    submit_es_response: BranchResponse = bc.send_recv_msg(
        BranchRequest("TRANSFEREXTRASOURCE", info_dict))

    match submit_es_response.statuscode:
        case BranchStatus.OK:
            blog.info("Switched to file transfer mode")

        case other:
            blog.error("Server did not switch to file transfer mode.")
            return

    blog.info("File transfer setup completed.")
    blog.info("Sending file..")

    if (os.path.getsize(file_path) == 0):
        blog.error("Filesize cannot be 0")
        return

    complete_es_response: BranchResponse = bc.send_file(file_path)

    match complete_es_response.statuscode:
        case BranchStatus.OK:
            blog.info("Extra source transfer completed.")

        case other:
            blog.error("Server did not acknowledge file transfer.")

    commit_es_response: BranchResponse = bc.send_recv_msg(
        BranchRequest("COMPLETETRANSFER", ""))

    match commit_es_response.statuscode:
        case BranchStatus.OK:
            blog.info("Extra source committed to database.")

        case other:
            blog.error("Couldn't commit to database.")


def view_extra_sources(bc):
    """
    Print a list of all managed extra sources

    :param bc: BranchClient
    """
    blog.info("Fetching available extra sources.")

    view_es_response: BranchResponse = bc.send_recv_msg(
        BranchRequest("GETMANAGEDEXTRASOURCES", ""))

    match view_es_response.statuscode:

        case BranchStatus.OK:
            print("\n\n{:<40} {:<50} {:<40}".format("ID", "FILENAME", "DESCRIPTION"))

            for es in view_es_response.payload:
                print("{:<40} {:<50} {:<40}".format(es["id"], es["filename"], es["description"]))

        case other:
            blog.error("Could not fetch list of extra sources.")


def remove_extra_source(bc, es_id: str):
    """
    Remove an extra source by id

    :param bc: BranchClient
    :param es_id: Id of extra source as str
    """
    extrasource_response: BranchResponse = bc.send_recv_msg(
        BranchRequest("REMOVEEXTRASOURCE", es_id))

    match extrasource_response.statuscode:

        case BranchStatus.OK:
            blog.info(f"Server: {extrasource_response.payload}")

        case other:
            blog.error(f"Server: {extrasource_response.payload}")
