import os
import re
import time

import blog
import packagebuild

from branchweb import webserver
from branchweb.usermanager import usermanager
from branchweb.usermanager import USER_FILE

from localstorage import packagestorage
from localstorage import pkgbuildstorage
from manager.manager import Manager
from manager.manager import Job

class branch_web_providers():

    usermgr: usermanager = None

    @staticmethod
    def setup_usermgr(file: str = USER_FILE):
        """
        Sets up the usermanager
        """
        branch_web_providers.usermgr = usermanager(file)

    @staticmethod
    def get_post_providers():
        post_providers = {
            "auth": branch_web_providers.auth_endpoint,
            "checkauth": branch_web_providers.check_auth_endpoint,
            "logoff": branch_web_providers.logoff_endpoint,
            "createuser": branch_web_providers.create_user_endpoint,
            "crossbuild": branch_web_providers.crossbuild_endpoint,
            "releasebuild": branch_web_providers.releasebuild_endpoint,
            "build": branch_web_providers.build_endpoint,
            "clearcompletedjobs": branch_web_providers.clear_completed_jobs_endpoint,
            "viewlog": branch_web_providers.viewjob_log_endpoint,
            "submitpackagebuild": branch_web_providers.submit_packagebuild_endpoint,
            "cancelqueuedjob": branch_web_providers.cancel_queued_job_endpoint,
            "cancelqueuedjobs": branch_web_providers.cancel_queued_jobs_endpoint,
            "deletepackage": branch_web_providers.delete_package_endpoint,
            "clientinfo": branch_web_providers.get_clientinfo
        }
        return post_providers
    
    @staticmethod
    def get_get_providers():
        get_providers = {
            "get": branch_web_providers.get_endpoint,
            "": branch_web_providers.root_endpoint
        }
        return get_providers

    #
    # endpoint used to authenticate a user
    #
    # ENDPOINT /auth (POST)
    @staticmethod
    def auth_endpoint(httphandler, form_data, post_data):
        # invalid request
        if("user" not in post_data or "pass" not in post_data):
            blog.debug("Missing request data for authentication")
            httphandler.send_web_response(webserver.webstatus.MISSING_DATA, "Missing request data for authentication")
            return

        p_user = post_data["user"]
        p_pass = post_data["pass"]

        user = branch_web_providers.usermgr.get_user(p_user)

        if (user is None):
            blog.debug("Failed to authenticate user '{}': Not registered".format(p_user))
            httphandler.send_web_response(webserver.webstatus.AUTH_FAILURE, "Authentication failed: user {} is not registered.".format(p_user))
            return

        authkey = user.authenticate(p_pass)

        if (authkey is None):
            blog.debug("Authentication failure")
            httphandler.send_web_response(webserver.webstatus.AUTH_FAILURE, "Authentication failed.")
        else:
            blog.debug("Authentication succeeded for user {} with new autkey {}".format(user.name, authkey.key_id))
            httphandler.send_web_response(webserver.webstatus.SUCCESS, "{}".format(authkey.key_id))

    #
    # checks if the user is logged in or not
    #
    # ENDPOINT /checkauth (POST)
    @staticmethod
    def check_auth_endpoint(httphandler, form_data, post_data):
        if("authkey" not in post_data):
            blog.debug("Missing request data for authentication: authkey")
            httphandler.send_web_response(webserver.webstatus.MISSING_DATA, "Missing request data for authentication: Authentication key (authkey)")
            return

        authkey = post_data["authkey"]

        user = branch_web_providers.usermgr.get_key_owner(authkey)

        if (user is None):
            blog.debug("Authkey {} was tested for validity: FALSE".format(authkey))
            httphandler.send_web_response(webserver.webstatus.AUTH_FAILURE, "Authkey {} is invalid.".format(authkey))
        else:
            if (user.authkeys[authkey].has_expired(time.time(), webserver.WEB_CONFIG["key_timeout"])):
                blog.debug("Authkey {} was tested for validity: EXPIRED".format(authkey))
                httphandler.send_web_response(webserver.webstatus.AUTH_FAILURE, "Authkey {} is invalid.".format(authkey))
            else:
                blog.debug("Authkey {} was tested for validity: TRUE, refreshing timestamp".format(authkey))
                user.authkeys[authkey].refresh()
                httphandler.send_web_response(webserver.webstatus.SUCCESS, "Authkey {} is valid.".format(authkey))

    #
    # destroys the specified session and logs the user off
    #
    # ENDPOINT /logoff (POST)
    @staticmethod
    def logoff_endpoint(httphandler, form_data, post_data):
        if("authkey" not in post_data):
            blog.debug("Missing request data for authentication: authkey")
            httphandler.send_web_response(webserver.webstatus.MISSING_DATA, "Missing request data for authentication: Authentication key (authkey)")
            return

        authkey = post_data["authkey"]
        user = branch_web_providers.usermgr.revoke_authkey(authkey)

        if (user is None):
            blog.debug("Tried to revoke invalid authkey {}".format(authkey))
            httphandler.send_web_response(webserver.webstatus.AUTH_FAILURE, "Invalid authentication key.")
        else:
            blog.debug("Authkey {}, owned by {} was revoked".format(authkey, user.name))
            httphandler.send_web_response(webserver.webstatus.SUCCESS, "Logoff acknowledged.")
 
    #
    # creates a webuser
    #
    # ENDPOINT /createuser (POST)
    @staticmethod
    def create_user_endpoint(httphandler, form_data, post_data):
        if("authkey" not in post_data):
            blog.debug("Missing request data for authentication: authkey")
            httphandler.send_web_response(webserver.webstatus.MISSING_DATA, "Missing request data for authentication: Authentication key (authkey)")
            return

        if("cuser" not in post_data):
            blog.debug("Missing request data for user creation: Username (cuser)")
            httphandler.send_web_response(webserver.webstatus.MISSING_DATA, "Missing request data for user creation: User (user)")
            return

        if("cpass" not in post_data):
            blog.debug("Missing request data for user creation: Password (cpass)")
            httphandler.send_web_response(webserver.webstatus.MISSING_DATA, "Missing request data for user creation: Password (pass)")
            return

        authkey = post_data["authkey"]
        nuser = post_data["cuser"]
        npass = post_data["cpass"]

        host_user = branch_web_providers.usermgr.get_key_owner(authkey)

        # Check if the user creating the new user is authenticated
        if (host_user is None):
            blog.debug("Unauthenticated user tried to create new user")
            httphandler.send_web_response(webserver.webstatus.AUTH_FAILURE, "Invalid authentication key.")
            return

        blog.debug("Refreshing authkey {} for user {}".format(authkey, host_user.name))
        host_user.authkeys[authkey].refresh()

        # Only root can create users
        if (host_user.name != "root"):
            blog.debug("Only root can create users!")
            httphandler.send_web_response(webserver.webstatus.AUTH_FAILURE, "Only root can create users.")
            return

        if(bool(re.match('^[a-zA-Z0-9]*$', nuser)) == False):
            blog.debug("Invalid username for account creation")
            httphandler.send_web_response(webserver.webstatus.SERV_FAILURE, "Invalid username for account creation")
            return

        if(not branch_web_providers.usermgr.add_user(nuser, npass)):
            httphandler.send_web_response(webserver.webstatus.SERV_FAILURE, "User already exists.")
            return

        httphandler.send_web_response(webserver.webstatus.SUCCESS, "User created")

    @staticmethod 
    def crossbuild_endpoint(httphandler, form_data, post_data):
        branch_web_providers.build_endpoint(httphandler, form_data, post_data, True)

    @staticmethod
    def releasebuild_endpoint(httphandler, form_data, post_data):
        branch_web_providers.build_endpoint(httphandler, form_data, post_data, False)

    #
    # request a release/cross build from the server
    #
    # ENDPOINT /build (POST) 
    @staticmethod
    def build_endpoint(httphandler, form_data, post_data, use_crosstools):
        if("authkey" not in post_data):
            blog.debug("Missing request data for authentication: authkey")
            httphandler.send_web_response(webserver.webstatus.MISSING_DATA, "Missing request data for authentication: Authentication key (authkey)")
            return

        authkey = post_data["authkey"]

        user = branch_web_providers.usermgr.get_key_owner(authkey)

        # Check if the user creating the new user is authenticated
        if (user is None):
            blog.debug("Unauthenticated user tried to create a build job")
            httphandler.send_web_response(webserver.webstatus.AUTH_FAILURE, "Invalid authentication key.")
            return

        blog.debug("Updating authkey {} for user {}".format(authkey, user.name))
        user.authkeys[authkey].refresh()

        if("pkgname" not in post_data):
            blog.debug("Missing request data for build request: Package name (pkgname)")
            httphandler.send_web_response(webserver.webstatus.MISSING_DATA, "Missing request data for package build: Package name (pkgname)")
            return

        pkgname = post_data["pkgname"]

        # request pkgbuild from branch manager
        if(pkgname in pkgbuildstorage.storage.get_all_packagebuild_names()):
            blog.info("Web client '{}' requested build for {}".format(user.name, pkgname))
             
            pkgbuild = pkgbuildstorage.storage.get_packagebuild_obj(pkgname)

            Manager.get_queue().add_job(Job(True, pkgbuild, user.name))
            Manager.get_scheduler().schedule()
            httphandler.send_web_response(webserver.webstatus.SUCCESS, "Package build queued successfully.")
        else:
            blog.info("Web client requested release build for invalid package.")
            httphandler.send_web_response(webserver.webstatus.SERV_FAILURE, "No such package available: {}".format(pkgname))

    #
    # Clears all completd jobs
    #
    # ENDPOINT /clearcompletedjobs (POST)
    @staticmethod
    def clear_completed_jobs_endpoint(httphandler, form_data, post_data):
        if("authkey" not in post_data):
            blog.debug("Missing request data for authentication: authkey")
            httphandler.send_web_response(webserver.webstatus.MISSING_DATA, "Missing request data for authentication: Authentication key (authkey)")
            return

        authkey = post_data["authkey"]

        user = branch_web_providers.usermgr.get_key_owner(authkey)

        # Check if the user creating the new user is authenticated
        if (user is None):
            blog.debug("Unauthenticated user tried to clear completed jobs")
            httphandler.send_web_response(webserver.webstatus.AUTH_FAILURE, "Invalid authentication key.")
            return

        blog.debug("Updating authkey {} for user {}".format(authkey, user.name))
        user.authkeys[authkey].refresh()

        Manager.get_queue().clear_completed_jobs()
        httphandler.send_web_response(webserver.webstatus.SUCCESS, "Completed jobs cleared successfully")

    #
    # Delete a specified packagebuild
    #
    # ENDPOINT /deletepackagebuild
    @staticmethod
    def delete_package_endpoint(httphandler, form_data, post_data):
        if("authkey" not in post_data):
            blog.debug("Missing request data for authentication: authkey")
            httphandler.send_web_response(webserver.webstatus.MISSING_DATA, "Missing request data for authentication: Authentication key (authkey)")
            return

        authkey = post_data["authkey"]

        user = branch_web_providers.usermgr.get_key_owner(authkey)

        # Check if the user creating the new user is authenticated
        if (user is None):
            blog.debug("Unauthenticated user tried to delete package")
            httphandler.send_web_response(webserver.webstatus.AUTH_FAILURE, "Invalid authentication key.")
            return

        blog.debug("Updating authkey {} for user {}".format(authkey, user.name))
        user.authkeys[authkey].refresh()

        if(not "pkgname" in post_data):
            httphandler.send_web_response(webserver.webstatus.MISSING_DATA, "Missing request data: Package name (pkgname)")
            return

        pkg_name = post_data["pkgname"]

        # cant delete crosstools if they are enabled
        if(pkg_name == "crosstools"):
            if(Manager.deployment_config["deploy_crossroot"]):
                httphandler.send_web_response(webserver.webstatus.SERV_FAILURE, "Cannot delete package 'crosstools', because it is part of the current deployment configuration.")
                return
        
        # cant delete realroot packages if they are enabled.
        if(pkg_name in Manager.deployment_config["realroot_packages"]):
            if(Manager.deployment_config["deploy_realroot"]):
                httphandler.send_web_response(webserver.webstatus.SERV_FAILURE, "Cannot delete package '{}', because it is part of the current deployment configuration.".format(pkg_name))
                return

        if(not pkg_name in pkgbuildstorage.storage.get_all_packagebuild_names()):
            httphandler.send_web_response(webserver.webstatus.MISSING_DATA, "No such pkgbuild found: {}".format(pkg_name))
            return

        blog.debug("Deleting packagebuild..")
        pkgbuildstorage.storage.remove_packagebuild(pkg_name)
        blog.debug("Deleting package..")
        
        # not locked, can delete
        if(not packagestorage.storage.check_package_lock(pkg_name)):
            packagestorage.storage().remove_package(pkg_name)
            httphandler.send_web_response(webserver.webstatus.SUCCESS, "Package and packagebuild deleted.")

        else:
            blog.warn("Package requested for deletion is currently locked, added to deletion queue.")
            packagestorage.storage.deletion_queue.append(pkg_name)
            httphandler.send_web_response(webserver.webstatus.SUCCESS, "Package is currently locked. Added to deletion queue.")

    #
    # Returns a json joblist 
    #
    # ENDPOINT /viewlog (POST)
    @staticmethod
    def viewjob_log_endpoint(httphandler, form_data, post_data):
        if("authkey" not in post_data):
            blog.debug("Missing request data for authentication: authkey")
            httphandler.send_web_response(webserver.webstatus.MISSING_DATA, "Missing request data for authentication: Authentication key (authkey)")
            return

        authkey = post_data["authkey"]

        user = branch_web_providers.usermgr.get_key_owner(authkey)

        # Check if the user creating the new user is authenticated
        if (user is None):
            blog.debug("Unauthenticated user tried to view job log")
            httphandler.send_web_response(webserver.webstatus.AUTH_FAILURE, "Invalid authentication key.")
            return

        blog.debug("Updating authkey {} for user {}".format(authkey, user.name))
        user.authkeys[authkey].refresh()

        if("jobid" not in post_data):
            blog.debug("Missing request data for viewlog")
            httphandler.send_web_response(webserver.webstatus.MISSING_DATA, "Missing request data for viewlog: Job ID (jobid)")
            return

        jobid = post_data["jobid"]
        job = Manager.get_queue().get_job_by_id(jobid)
            
        if(job is None):
            httphandler.send_web_response(webserver.webstatus.SERV_FAILURE, "Invalid job id: {}".format(jobid))
            return

        if(job.build_log is None):
            httphandler.send_web_response(webserver.webstatus.SERV_FAILURE, "No build log available.")
            return

        httphandler.send_web_response(webserver.webstatus.SUCCESS, job.build_log)
        
    #
    # Post endpoint to submit a package build
    #
    # ENDPOINT /submitpackagebuild (POST) 
    @staticmethod
    def submit_packagebuild_endpoint(httphandler, form_data, post_data):
        if("authkey" not in post_data):
            blog.debug("Missing request data for authentication: authkey")
            httphandler.send_web_response(webserver.webstatus.MISSING_DATA, "Missing request data for authentication: Authentication key (authkey)")
            return

        authkey = post_data["authkey"]

        user = branch_web_providers.usermgr.get_key_owner(authkey)

        # Check if the user creating the new user is authenticated
        if (user is None):
            blog.debug("Unauthenticated user tried to submit a package build")
            httphandler.send_web_response(webserver.webstatus.AUTH_FAILURE, "Invalid authentication key.")
            return

        blog.debug("Updating authkey {} for user {}".format(authkey, user.name))
        user.authkeys[authkey].refresh()

        if("packagebuild" not in post_data):
            blog.debug("Missing request data for package submission: Package build (packagebuild)")
            httphandler.send_web_response(webserver.webstatus.MISSING_DATA, "Missing package build.")
            return
        
        blog.debug("Checking submission..")
        package_build = packagebuild.package_build.from_string(post_data["packagebuild"])

        if(not package_build.is_valid()):
            httphandler.send_web_response(webserver.webstatus.SERV_FAILURE, "Missing values in package build")
            return
        
        pkgbuildstorage.storage.add_packagebuild_obj(package_build)
        httphandler.send_web_response(webserver.webstatus.SUCCESS, "Package submission accepted.")


    #
    # get= endpoint main function
    #
    @staticmethod
    def get_endpoint(httphandler, form_data):
        match form_data["get"]:
            case "packagelist":
                branch_web_providers.get_endpoint_pkglist(httphandler)
                return
            case "package":
                branch_web_providers.get_endpoint_package(httphandler, form_data)
                return
            case "versions":
                branch_web_providers.get_endpoint_versions(httphandler, form_data)
                return
            case "packagebuildlist":
                branch_web_providers.get_endpoint_pkgbuildlist(httphandler)
                return
            case "joblist":
                branch_web_providers.get_endpoint_jobs(httphandler)
                return
            case "packagebuild":
                branch_web_providers.get_endpoint_pkgbuild(httphandler, form_data)
                return
            case "clientlist":
                branch_web_providers.get_endpoint_clientlist(httphandler)
                return
            case default:
                httphandler.generic_malformed_request()
                return

    #
    # Gets a list of queued, running, completed jobs
    #
    # ENDPOINT /?get=joblist (GET)
    @staticmethod
    def get_endpoint_jobs(httphandler):
        completed_jobs = Manager.get_queue().get_completed_jobs()
        running_jobs = Manager.get_queue().get_running_jobs()
        queued_jobs = Manager.get_queue().get_queued_jobs()

        all_jobs = {
            "completed_jobs": [obj.get_info_dict() for obj in completed_jobs],
            "running_jobs": [obj.get_info_dict() for obj in running_jobs],
            "queued_jobs": [obj.get_info_dict() for obj in queued_jobs]
        }

        httphandler.send_web_response(webserver.webstatus.SUCCESS, all_jobs)

    #
    # Gets a pkgbuild file
    #
    # ENDPOINT /?get=packagebuild
    @staticmethod
    def get_endpoint_pkgbuild(httphandler, form_data):
        if("pkgname" not in form_data):
            httphandler.send_web_response(webserver.webstatus.MISSING_DATA, "Missing request data")
            return

        if(form_data["pkgname"] in pkgbuildstorage.storage.get_all_packagebuild_names()):
            httphandler.send_web_response(webserver.webstatus.SUCCESS, pkgbuildstorage.storage.get_packagebuild_obj(form_data["pkgname"]).get_string())
        else:
            httphandler.send_web_response(webserver.webstatus.SERV_FAILURE, "Invalid packagebuild name.")

    #
    # Gets a list of conected clients
    # 
    # ENDPOINT /?get=clientlist
    @staticmethod
    def get_endpoint_clientlist(httphandler):
        clients: list = Manager.get_controller_names()
        buildbots: list = Manager.get_buildbot_names()

        _dict = {
            "controllers": clients,
            "buildbots": buildbots
        }

        httphandler.send_web_response(webserver.webstatus.SUCCESS, _dict)
    
    #
    # Get client info dictionary
    #
    # ENDPOINT /clientinfo (POST)
    @staticmethod
    def get_clientinfo(httphandler, form_data, post_data):
        if("authkey" not in post_data):
            blog.debug("Missing request data for authentication: authkey")
            httphandler.send_web_response(webserver.webstatus.MISSING_DATA, "Missing request data for authentication: Authentication key (authkey)")
            return

        authkey = post_data["authkey"]

        user = branch_web_providers.usermgr.get_key_owner(authkey)

        # Check if the user creating the new user is authenticated
        if (user is None):
            blog.debug("Unauthenticated user tried to retrieve client info")
            httphandler.send_web_response(webserver.webstatus.AUTH_FAILURE, "Invalid authentication key.")
            return

        blog.debug("Updating authkey {} for user {}".format(authkey, user.name))
        user.authkeys[authkey].refresh()

        if("clientname" not in post_data):
            httphandler.send_web_response(webserver.webstatus.MISSING_DATA, "Missing request data for clientinfo: Client name (clientname)")
            return
        
        target_client: list = Manager.get_client_by_name(post_data["clientname"])
        if(target_client == None):
            httphandler.send_web_response(webserver.webstatus.SERV_FAILURE, "Invalid client name.")
            return
        
        httphandler.send_web_response(webserver.webstatus.SUCCESS, target_client.get_sysinfo())


    #
    # Gets a list of all available packages
    #
    # ENDPOINT /?get=packagelist (GET)
    @staticmethod
    def get_endpoint_pkglist(httphandler):
        stor = packagestorage.storage()
        meta_inf = stor.get_all_package_meta()

        dict_arr = [ ]
        req_line = httphandler.headers._headers[0][1]

        for meta in meta_inf:
            real_version = meta.get_latest_real_version()
            
            url = "http://{}/?get=package&pkgname={}".format(req_line, meta.get_name())

            _dict = {
                "name" : meta.get_name(),
                "real_version": real_version,
                "version": meta.get_version(real_version),
                "description": meta.get_description(),
                "dependencies": meta.get_dependencies(real_version),
                "hash": meta.get_hash(real_version),
                "url": url
            }

            dict_arr.append(_dict)

        httphandler.send_web_response(webserver.webstatus.SUCCESS, dict_arr)
    
    #
    # Cancels all currently queued jobs 
    #
    # ENDPOINT /cancelqueuedjobs (POST)
    @staticmethod
    def cancel_queued_jobs_endpoint(httphandler, form_data, post_data):
        if("authkey" not in post_data):
            blog.debug("Missing request data for authentication: authkey")
            httphandler.send_web_response(webserver.webstatus.MISSING_DATA, "Missing request data for authentication: Authentication key (authkey)")
            return

        authkey = post_data["authkey"]

        user = branch_web_providers.usermgr.get_key_owner(authkey)

        # Check if the user creating the new user is authenticated
        if (user is None):
            blog.debug("Unauthenticated user tried to cancel queud jobs")
            httphandler.send_web_response(webserver.webstatus.AUTH_FAILURE, "Invalid authentication key.")
            return

        blog.debug("Updating authkey {} for user {}".format(authkey, user.name))
        user.authkeys[authkey].refresh()

        Manager.get_queue().cancel_queued_jobs()
        httphandler.send_web_response(webserver.webstatus.SUCCESS, "Waiting jobs cancelled.")

    #
    # Cancels a currently queued job 
    #
    # ENDPOINT /cancelqueuedjob (POST)
    @staticmethod
    def cancel_queued_job_endpoint(httphandler, form_data, post_data):
        if("authkey" not in post_data):
            blog.debug("Missing request data for authentication: authkey")
            httphandler.send_web_response(webserver.webstatus.MISSING_DATA, "Missing request data for authentication: Authentication key (authkey)")
            return

        authkey = post_data["authkey"]

        user = branch_web_providers.usermgr.get_key_owner(authkey)

        # Check if the user creating the new user is authenticated
        if (user is None):
            blog.debug("Unauthenticated user tried to cancel a queued job")
            httphandler.send_web_response(webserver.webstatus.AUTH_FAILURE, "Invalid authentication key.")
            return

        blog.debug("Updating authkey {} for user {}".format(authkey, user.name))
        user.authkeys[authkey].refresh()

        if(not "jobid" in post_data):
            httphandler.send_web_response(webserver.webstatus.MISSING_DATA, "Missing request data: Job ID (jobid)")
            return
        
        job = Manager.get_queue().get_job_by_id(post_data["jobid"])

        if(job == None):
            httphandler.send_web_response(webserver.webstatus.SERV_FAILURE, "Invalid job ID.")
            return
        
        Manager.get_queue().cancel_queued_job(job)
        httphandler.send_web_response(webserver.webstatus.SUCCESS, "Waiting job cancelled.")

    #
    # Gets a list of all available package builds
    #
    # ENDPOINT /?get=jsonpackagebuildlist (GET)
    @staticmethod
    def get_endpoint_pkgbuildlist(httphandler):
        httphandler.send_web_response(webserver.webstatus.SUCCESS, pkgbuildstorage.storage.get_all_packagebuild_names())

    #
    # Endpoint specifically for leaf.
    # returns non-json response
    #
    # fetches a package file
    #
    # ENDPOINT: /?get=package (GET)
    @staticmethod
    def get_endpoint_package(httphandler, form_data):
        stor = packagestorage.storage()

        
        package_file = None
        package_full_name = ""

        form_keys = form_data.keys()
        
        # missing post data
        if(not "pkgname" in form_keys):
            httphandler.send_str_raw(400, "E_PKGNAME")
            return

        # Package doesn't exist
        if(not form_data["pkgname"] in stor.packages):
            httphandler.send_str_raw(404, "E_PACKAGE")
            return
            
        # Get the meta file for that package
        meta = stor.get_meta_by_name(form_data["pkgname"])

        # We have a version tag, get specific version.
        if("version" in form_keys):
            # Construct the full package name
            package_full_name = form_data["pkgname"] + "-" + meta.get_version(form_data["version"])

            # Construct the package path
            package_file = stor.get_pkg_path(form_data["pkgname"], form_data["version"])

        # No version tag, get latest
        else:
            # latest version, no version tag
            latest_version = meta.get_latest_real_version()

            # Construct the full package name
            package_full_name = form_data["pkgname"] + "-" + meta.get_version(latest_version)

            # Construct the package path
            package_file = stor.get_pkg_path(form_data["pkgname"], latest_version)

            # Could not find latest version (Shouldn't happen..?), notify failure.
            if(package_file is None):
                httphandler.send_str_raw(404, "E_VERSION")
                return 

        # Couldn't find package file..
        if(package_file is None):
            httphandler.send_str_raw(404, "E_PACKAGE")
            return

        pfile = open(package_file, "rb")

        # register a file lock
        file_lock_id = packagestorage.storage.register_active_download(form_data["pkgname"])

        # Send the file to the client
        httphandler.send_file(pfile, os.path.getsize(package_file), package_full_name + ".lfpkg")

        # unregister a file lock
        packagestorage.storage.unregister_active_download(file_lock_id)

    #
    # / endpoint, returns html page
    #
    # ENDPOINT: / (GET)
    @staticmethod
    def root_endpoint(httphandler, form_data):
        httphandler.send_str_raw(200, "<h1>Bad request.</h1>")

