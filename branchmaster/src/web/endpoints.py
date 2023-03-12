import json
import os
import re

import blog
import packagebuild

from branchweb import webserver
from branchweb import webauth  

from localstorage import packagestorage
from localstorage import pkgbuildstorage
from manager import manager

class branch_web_providers():
    
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
            "deletepackage": branch_web_providers.delete_package_endpoint
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
        
        if(webauth.web_auth.validate_pw(post_data["user"], post_data["pass"])):
            blog.debug("Authentication succeeded.")
            key = webauth.web_auth.new_authorized_key()
            
            httphandler.send_web_response(webserver.webstatus.SUCCESS, "{}".format(key.key_id))
        
        else:
            blog.debug("Authentication failure")
            httphandler.send_web_response(webserver.webstatus.AUTH_FAILURE, "Authentication failed.")

    #
    # checks if the user is logged in or not
    #
    # ENDPOINT /checkauth (POST)
    @staticmethod
    def check_auth_endpoint(httphandler, form_data, post_data):
        if("authkey" not in post_data):
            httphandler.send_web_response(webserver.webstatus.MISSING_DATA, "Missing request data for authentication.")    
            return
        
        if(webauth.web_auth.validate_key(post_data["authkey"])):
            httphandler.send_web_response(webserver.webstatus.SUCCESS, "Authentication succeeded.")
            
        else:
            httphandler.send_web_response(webserver.webstatus.AUTH_FAILURE, "Authentication failed.")
            
    #
    # destroys the specified session and logs the user off
    #
    # ENDPOINT /logoff (POST)
    @staticmethod
    def logoff_endpoint(httphandler, form_data, post_data):
        if("authkey" not in post_data):
            httphandler.send_web_response(webserver.webstatus.MISSING_DATA, "Missing request data for authentication.")
            return

        # check if logged in       
        if(webauth.web_auth.validate_key(post_data["authkey"])):
            webauth.web_auth.invalidate_key(post_data["authkey"])
            httphandler.send_web_response(webserver.webstatus.SUCCESS, "Logoff acknowledged.")
            
        else:
            httphandler.send_web_response(webserver.webstatus.AUTH_FAILURE, "Invalid authentication key.")
            
 
    #
    # creates a webuser
    #
    # ENDPOINT /createuser (POST)
    @staticmethod
    def create_user_endpoint(httphandler, form_data, post_data):
        if("authkey" not in post_data):
            httphandler.send_web_response(webserver.webstatus.MISSING_DATA, "Missing request data for authentication.")
            return

        # check if logged in
        if(not webauth.web_auth.validate_key(post_data["authkey"])):
            httphandler.send_web_response(webserver.webstatus.AUTH_FAILURE, "Invalid authentication key.")
            return


        if("cuser" not in post_data or "cpass" not in post_data):
            blog.debug("Missing request data for user creation")
            httphandler.send_web_response(webserver.webstatus.MISSING_DATA, "Missing request data for user creation.")
            return
        
        cuser = post_data["cuser"]
        cpass = post_data["cpass"]
        
        if(bool(re.match('^[a-zA-Z0-9]*$', cuser)) == False):
            blog.debug("Invalid username for account creation")
            httphandler.send_web_response(webserver.webstatus.SERV_FAILURE, "Invalid username for account creation..")
            return
        
        if(not webauth.web_auth.usermgr.add_user(cuser, cpass)):
            httphandler.send_web_response(webserver.webstatus.SERV_FAILURE, "User already exists.")
            return

        httphandler.send_web_response(webserver.webstatus.SUCCESS, "User created.")
    
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
            blog.debug("Missing request data for authentication")
            httphandler.send_web_response(webserver.webstatus.MISSING_DATA, "Missing request data for authentication.")
            
            return

        # check if logged in
        if(not webauth.web_auth.validate_key(post_data["authkey"])):
            httphandler.send_web_response(webserver.webstatus.AUTH_FAILURE, "Invalid authentication key.")
            
            return

        if("pkgname" not in post_data):
            blog.debug("Missing request data for build request: pkgname")
            httphandler.send_web_response(webserver.webstatus.MISSING_DATA, "Missing request data for package build.")
            
            return

        pkgname = post_data["pkgname"]

        # request pkgbuild from branch manager
        if(pkgname in pkgbuildstorage.storage.get_all_packagebuild_names()):
            blog.info("Web client requested build for {}".format(pkgname))
             
            pkg = pkgbuildstorage.storage.get_packagebuild_obj(pkgname)

            # get a job obj, use_crosstools = True
            job = manager.manager.new_job(use_crosstools)

            job.pkg_payload = pkg
            job.requesting_client = "webclient"
            job.set_status("WAITING")
            
            res = manager.manager.get_queue().add_to_queue(job)
            httphandler.send_web_response(webserver.webstatus.SUCCESS, "Package build queued successfully: {}.".format(res))
        else:
            blog.info("Web client requested release build for invalid package.")
            httphandler.send_web_response(webserver.webstatus.SERV_FAILURE, "No such package available.")

    #
    # Clears all completd jobs
    #
    # ENDPOINT /clearcompletedjobs (POST)
    @staticmethod
    def clear_completed_jobs_endpoint(httphandler, form_data, post_data):
        if("authkey" not in post_data):
            blog.debug("Missing request data for authentication")
            httphandler.send_web_response(webserver.webstatus.MISSING_DATA, "Missing request data for authentication.")
            return

        # check if logged in
        if(not webauth.web_auth.validate_key(post_data["authkey"])):
            httphandler.send_web_response(webserver.webstatus.AUTH_FAILURE, "Invalid authentication key.")
            return
        
        manager.manager.clear_completed_jobs()  
        httphandler.send_web_response(webserver.webstatus.SUCCESS, "Completed jobs cleared successfully")

    #
    # Delete a specified packagebuild
    #
    # ENDPOINT /deletepackagebuild
    @staticmethod
    def delete_package_endpoint(httphandler, form_data, post_data):
        if("authkey" not in post_data):
            httphandler.send_web_response(webserver.webstatus.MISSING_DATA, "Missing request data for authentication.")    
            return
        
        if(not webauth.web_auth.validate_key(post_data["authkey"])):
            httphandler.send_web_response(webserver.webstatus.AUTH_FAILURE, "Authentication failed.")
            return

        if(not "pkgname" in post_data):
            httphandler.send_web_response(webserver.webstatus.MISSING_DATA, "Missing request data: pkgname")
            return
         
        pkg_name = post_data["pkgname"]

        # cant delete crosstools if they are enabled
        if(pkg_name == "crosstools"):
            if(manager.manager.deployment_config["deploy_crossroot"]):
                httphandler.send_web_response(webserver.webstatus.SERV_FAILURE, "Cannot delete package 'crosstools', because it is part of the current deployment configuration.")
                return
        
        # cant delete realroot packages if they are enabled.
        if(pkg_name in manager.manager.deployment_config["realroot_packages"]):
            if(manager.manager.deployment_config["deploy_realroot"]):
                httphandler.send_web_response(webserver.webstatus.SERV_FAILURE, "Cannot delete package '{}', because it is part of the current deployment configuration.".format(pkg_name))
                return

        if(not pkg_name in pkgbuildstorage.storage.get_all_packagebuild_names()):
            httphandler.send_web_response(webserver.webstatus.MISSING_DATA, "No such pkgbuild found.")
            return

        blog.debug("Deleting packagebuild..")
        pkgbuildstorage.storage.remove_packagebuild(pkg_name)
        blog.debug("Deleting package..")
        
        # not locked, can delete
        if(not packagestorage.storage.check_package_lock(pkg_name)):
            packagestorage.storage().remove_package(pkg_name)
            httphandler.send_web_response(webserver.webstatus.MISSING_DATA, "Package and packagebuild deleted.")

        else:
            blog.warn("Package requested for deletion is currently locked, added to deletion queue.")
            packagestorage.storage.deletion_queue.append(pkg_name)
            httphandler.send_web_response(webserver.webstatus.MISSING_DATA, "Package is currently locked. Added to deletion queue.")

    #
    # Returns a json joblist 
    #
    # ENDPOINT /viewlog (POST)
    @staticmethod
    def viewjob_log_endpoint(httphandler, form_data, post_data):
        if("authkey" not in post_data):
            blog.debug("Missing request data for authentication")
            httphandler.send_web_response(webserver.webstatus.MISSING_DATA, "Missing request data for viewlog: authkey")
            
            return

        # check if logged in
        if(not webauth.web_auth.validate_key(post_data["authkey"])):
            blog.debug("Missing authentication key")
            httphandler.send_web_response(webserver.webstatus.AUTH_FAILURE, "Invalid authentication key.")
            return
        
        if("jobid" not in post_data):
            blog.debug("Missing request data for viewlog")
            httphandler.send_web_response(webserver.webstatus.MISSING_DATA, "Missing request data for viewlog: jobid")
            return

        jobid = post_data["jobid"]
        job = manager.manager.get_job_by_id(jobid)
            
        if(job is None):
            httphandler.send_web_response(webserver.webstatus.SERV_FAILURE, "Invalid job id specified.")
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
            blog.debug("Missing request data for authentication")
            httphandler.send_web_response(webserver.webstatus.MISSING_DATA, "Missing request data for viewlog: authkey")
            return

        # check if logged in
        if(not webauth.web_auth.validate_key(post_data["authkey"])):
            blog.debug("Missing authentication key")
            httphandler.send_web_response(webserver.webstatus.AUTH_FAILURE, "Invalid authentication key.")        
            return
            
        if("packagebuild" not in post_data):
            blog.debug("Missing request data for package submission")
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
        manager_obj = manager.manager

        completed_jobs = manager_obj.get_completed_jobs()
        running_jobs = manager_obj.get_running_jobs()
        queued_jobs = manager_obj.get_queued_jobs()


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
        clients = manager.manager.get_controller_names()
        buildbots = manager.manager.get_buildbot_names()

        _dict = {
            "controllers": clients,
            "buildbots": buildbots
        }

        httphandler.send_web_response(webserver.webstatus.SUCCESS, _dict)


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
            httphandler.send_web_response(webserver.webstatus.MISSING_DATA, "Missing request data for authentication.")    
            return
        
        if(not webauth.web_auth.validate_key(post_data["authkey"])):
            httphandler.send_web_response(webserver.webstatus.AUTH_FAILURE, "Authentication failed.")
        
        manager.manager.cancel_all_queued_jobs()
        httphandler.send_web_response(webserver.webstatus.SUCCESS, "Waiting jobs cancelled.")

    #
    # Cancels a currently queued job 
    #
    # ENDPOINT /cancelqueuedjob (POST)
    @staticmethod
    def cancel_queued_job_endpoint(httphandler, form_data, post_data):
        if("authkey" not in post_data):
            httphandler.send_web_response(webserver.webstatus.MISSING_DATA, "Missing request data for authentication.")    
            return
        
        if(not webauth.web_auth.validate_key(post_data["authkey"])):
            httphandler.send_web_response(webserver.webstatus.AUTH_FAILURE, "Authentication failed.")
            return

        if(not "jobid" in post_data):
            httphandler.send_web_response(webserver.webstatus.MISSING_DATA, "Missing request data: Job ID")
            return
        
        job = manager.manager.get_job_by_id(post_data["jobid"])

        if(job == None):
            httphandler.send_web_response(webserver.webstatus.SERV_FAILURE, "Invalid job ID.")
            return 

        manager.manager.cancel_queued_job(job)
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

