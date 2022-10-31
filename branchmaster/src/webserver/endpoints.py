from enum import Enum
import json
import os
import re

from webserver import webauth
from webserver import webserver
from webserver import httputils
from webserver import usermanager
from log import blog
from localstorage import packagestorage
from localstorage import pkgbuildstorage
from manager import manager
from config import config

#
# endpoint class with path and corresponding handler function
#
class endpoint():
    def __init__(self, path, handler):
        self.path = path
        self.handlerfunc = handler
#
# webresponse class with response code and payload
#
class webresponse():
    def __init__(self, wstatus, payload):
        self.status = wstatus.name
        self.response_code = wstatus.value
        self.payload = payload

    def json_str(self):
        return json.dumps({ 
                "status": self.status,
                "response_code": self.response_code,
                "payload": self.payload
            })

class webstatus(Enum):
    SUCCESS = 200
    MISSING_DATA = 300
    SERV_FAILURE = 400
    AUTH_FAILURE = 500

def register_get_endpoints():
    blog.debug("Registering get endpoints..")
    webserver.register_endpoint(endpoint("get", get_endpoint))
    webserver.register_endpoint(endpoint("", root_endpoint))
    webserver.register_endpoint(endpoint("test", test_endpoint))

def register_post_endpoints():
    blog.debug("Registering post endpoints..")
    webserver.register_post_endpoint(endpoint("auth", auth_endpoint))
    webserver.register_post_endpoint(endpoint("checkauth", check_auth_endpoint))
    webserver.register_post_endpoint(endpoint("logoff", logoff_endpoint))
    webserver.register_post_endpoint(endpoint("createuser", create_user_endpoint))
    webserver.register_post_endpoint(endpoint("crossbuild", crossbuild_endpoint))
    webserver.register_post_endpoint(endpoint("releasebuild", releasebuild_endpoint))
    webserver.register_post_endpoint(endpoint("viewlog", viewjob_log_endpoint))
    webserver.register_post_endpoint(endpoint("clearcompletedjobs", clear_completed_jobs_endpoint))

#
# endpoint used to authenticate a user
#
# ENDPOINT /auth (POST)
def auth_endpoint(httphandler, form_data, post_data):
    httphandler.send_response(200)
    httphandler.send_header("Content-type", "text/plain")
    httphandler.end_headers()
    
    # invalid request
    if("user" not in post_data or "pass" not in post_data):
        blog.debug("Missing request data for authentication")
        wr = webresponse(webstatus.MISSING_DATA, "Missing request data for authentication.")
        httphandler.wfile.write(bytes(wr.json_str(), "utf-8"))
        return
    
    if(webauth.web_auth().validate_pw(post_data["user"], post_data["pass"])):
        blog.debug("Authentication succeeded.")
        key = webauth.web_auth().new_authorized_key() 
        httphandler.wfile.write(bytes(webresponse(webstatus.SUCCESS, "{}".format(key.key_id)).json_str(), "utf-8"))
    else:
        blog.debug("Authentication failure")
        wr = webresponse(webstatus.AUTH_FAILURE, "Authentication failed.")
        httphandler.wfile.write(bytes(wr.json_str(), "utf-8"))

#
# checks if the user is logged in or not
#
# ENDPOINT /checkauth (POST)
def check_auth_endpoint(httphandler, form_data, post_data):
    httphandler.send_response(200)
    httphandler.send_header("Content-type", "text/plain")
    httphandler.end_headers()

    if("authkey" not in post_data):
        wr = webresponse(webstatus.MISSING_DATA, "Missing request data for authentication.")
        httphandler.wfile.write(bytes(wr.json_str(), "utf-8"))
        return
    
    if(webauth.web_auth().validate_key(post_data["authkey"])):
        wr = webresponse(webstatus.SUCCESS, "Authentication succeeded.")
        httphandler.wfile.write(bytes(wr.json_str(), "utf-8"))
    else:
        wr = webresponse(webstatus.AUTH_FAILURE, "Authentication failed.")
        httphandler.wfile.write(bytes(wr.json_str(), "utf-8"))

#
# destroys the specified session and logs the user off
#
# ENDPOINT /logoff (POST)
def logoff_endpoint(httphandler, form_data, post_data):
    httphandler.send_response(200)
    httphandler.send_header("Content-type", "text/plain")
    httphandler.end_headers()
 
    if("authkey" not in post_data):
        wr = webresponse(webstatus.MISSING_DATA, "Missing request data for authentication.")
        httphandler.wfile.write(bytes(wr.json_str(), "utf-8"))
        return

    # check if logged in       
    if(webauth.web_auth().validate_key(post_data["authkey"])):
        webauth.web_auth().invalidate_key(post_data["authkey"])
        wr = webresponse(webstatus.SUCCESS, "Logoff acknowledged.")
        httphandler.wfile.write(bytes(wr.json_str(), "utf-8"))
    else:
        wr = webresponse(webstatus.AUTH_FAILURE, "Invalid authentication key.")
        httphandler.wfile.write(bytes(wr.json_str(), "utf-8"))
 
#
# creates a webuser
#
# ENDPOINT /createuser (POST)
def create_user_endpoint(httphandler, form_data, post_data):
    httphandler.send_response(200)
    httphandler.send_header("Content-type", "text/plain")
    httphandler.end_headers()

    if("authkey" not in post_data):
        wr = webresponse(webstatus.MISSING_DATA, "Missing request data for authentication.")
        httphandler.wfile.write(bytes(wr.json_str(), "utf-8"))
        return

    # check if logged in
    if(not webauth.web_auth().validate_key(post_data["authkey"])):
        wr = webresponse(webstatus.AUTH_FAILURE, "Invalid authentication key.")
        httphandler.wfile.write(bytes(wr.json_str(), "utf-8"))
        return


    if("cuser" not in post_data or "cpass" not in post_data):
        blog.debug("Missing request data for user creation")
        wr = webresponse(webstatus.MISSING_DATA, "Missing request data for user creation.")
        httphandler.wfile.write(bytes(wr.json_str(), "utf-8"))
        return
    
    cuser = post_data["cuser"]
    cpass = post_data["cpass"]
    
    if(bool(re.match('^[a-zA-Z0-9]*$', cuser)) == False):
        blog.debug("Invalid username for account creation")
        wr = webresponse(webstatus.SERV_FAILURE, "Invalid username for account creation..")
        httphandler.wfile.write(bytes(wr.json_str(), "utf-8"))
        return
    
    if(not usermanager.usermanager().add_user(cuser, cpass)):
        wr = webresponse(webstatus.SERV_FAILURE, "User already exists.")
        httphandler.wfile.write(bytes(wr.json_str(), "utf-8"))
        return

    wr = webresponse(webstatus.SUCCESS, "User created.")
    httphandler.wfile.write(bytes(wr.json_str(), "utf-8"))

def crossbuild_endpoint(httphandler, form_data, post_data):
    build_endpoint(httphandler, form_data, post_data, True)

def releasebuild_endpoint(httphandler, form_data, post_data):
    build_endpoint(httphandler, form_data, post_data, False)

#
# request a release/cross build from the server
#
# ENDPOINT /build (POST) 
def build_endpoint(httphandler, form_data, post_data, use_crosstools):
    httphandler.send_response(200)
    httphandler.send_header("Content-type", "text/plain")
    httphandler.end_headers()

    if("authkey" not in post_data):
        blog.debug("Missing request data for authentication")
        wr = webresponse(webstatus.MISSING_DATA, "Missing request data for authentication.")
        httphandler.wfile.write(bytes(wr.json_str(), "utf-8"))
        return

    # check if logged in
    if(not webauth.web_auth().validate_key(post_data["authkey"])):
        wr = webresponse(webstatus.AUTH_FAILURE, "Invalid authentication key.")
        httphandler.wfile.write(bytes(wr.json_str(), "utf-8"))
        return

    if("pkgname" not in post_data):
        blog.debug("Missing request data for build request: pkgname")
        wr = webresponse(webstatus.MISSING_DATA, "Missing request data for package build.")
        httphandler.wfile.write(bytes(wr.json_str(), "utf-8"))
        return

    pkgname = post_data["pkgname"]

    # request pkgbuild from branch manager
    storage = pkgbuildstorage.storage()
    if(pkgname in storage.packages):
        blog.info("Web client requested build for {}".format(pkgname))
         
        pkg = storage.get_bpb_obj(pkgname)
        mgr = manager.manager()

        # get a job obj, use_crosstools = True
        job = mgr.new_job(use_crosstools)

        # TODO: remove seperate build_pkg_name, because pkg contains it.
        job.build_pkg_name = pkg.name
        job.pkg_payload = pkg
        job.requesting_client = "webclient"
        job.set_status("WAITING")
        
        res = mgr.get_queue().add_to_queue(job)
        
        wr = webresponse(webstatus.SUCCESS, "Package build queued successfully: {}.".format(res))
        httphandler.wfile.write(bytes(wr.json_str(), "utf-8"))

    else:
        blog.info("Web client requested release build for invalid package.")
        wr = webresponse(webstatus.SERV_FAILURE, "No such package available.")
        httphandler.wfile.write(bytes(wr.json_str(), "utf-8"))


#
# Clears all completd jobs
#
# ENDPOINT /clearcompletedjobs (POST)
def clear_completed_jobs_endpoint(httphandler, form_data, post_data):
    httphandler.send_response(200)
    httphandler.send_header("Content-type", "text/plain")
    httphandler.end_headers()

    if("authkey" not in post_data):
        blog.debug("Missing request data for authentication")
        wr = webresponse(webstatus.MISSING_DATA, "Missing request data for authentication.")
        httphandler.wfile.write(bytes(wr.json_str(), "utf-8"))
        return

    # check if logged in
    if(not webauth.web_auth().validate_key(post_data["authkey"])):
        wr = webresponse(webstatus.AUTH_FAILURE, "Invalid authentication key.")
        httphandler.wfile.write(bytes(wr.json_str(), "utf-8"))
        return
    
    manager.manager().clear_completed_jobs()  
    wr = webresponse(webstatus.SUCCESS, "Completed jobs cleared successfully")
    httphandler.wfile.write(bytes(wr.json_str(), "utf-8"))


#
# Returns a json joblist 
#
# ENDPOINT /viewlog (POST)
def viewjob_log_endpoint(httphandler, form_data, post_data):
    httphandler.send_response(200)
    httphandler.send_header("Content-type", "text/plain")
    httphandler.end_headers()
 
    if("authkey" not in post_data):
        blog.debug("Missing request data for authentication")
        wr = webresponse(webstatus.MISSING_DATA, "Missing request data for viewlog: authkey")
        httphandler.wfile.write(bytes(wr.json_str(), "utf-8"))
        return

    # check if logged in
    if(not webauth.web_auth().validate_key(post_data["authkey"])):
        blog.debug("Missing authentication key")
        wr = webresponse(webstatus.AUTH_FAILURE, "Invalid authentication key.")
        httphandler.wfile.write(bytes(wr.json_str(), "utf-8"))
        return
    
    if("jobid" not in post_data):
        blog.debug("Missing request data for viewlog")
        wr = webresponse(webstatus.MISSING_DATA, "Missing request data for viewlog: jobid")
        httphandler.wfile.write(bytes(wr.json_str(), "utf-8"))
        return

    jobid = post_data["jobid"]
    
    job = manager.manager().get_job_by_id(jobid)
        
    if(job is None):
        wr = webresponse(webstatus.SERV_FAILURE, "Invalid job id specified.")
        httphandler.wfile.write(bytes(wr.json_str(), "utf-8"))
        return

    if(job.build_log is None):
        wr = webresponse(webstatus.SERV_FAILURE, "No build log available.")
        httphandler.wfile.write(bytes(wr.json_str(), "utf-8"))
        return

    wr = webresponse(webstatus.SUCCESS, job.build_log)
    httphandler.wfile.write(bytes(wr.json_str(), "utf-8"))

#
# get endpoint main function
#
def get_endpoint(httphandler, form_data):
    if(form_data["get"] == "packagelist"):
        get_endpoint_pkglist(httphandler)
    elif(form_data["get"] == "jsonpackagelist"):
        get_endpoint_json_pkglist(httphandler)
    elif(form_data["get"] == "package"):
        get_endpoint_package(httphandler, form_data)
    elif(form_data["get"] == "versions"):
        get_endpoint_versions(httphandler, form_data)
    elif(form_data["get"] == "jsonpackagebuildlist"):
        get_endpoint_json_pkgbuildlist(httphandler)
    elif(form_data["get"] == "joblist"):
        get_jobs_endpoint(httphandler)
    else:
        httputils.generic_malformed_request(httphandler)

#
# Gets a list of queued, running, completed jobs
#
# ENDPOINT /?get=joblist (GET)
def get_jobs_endpoint(httphandler):
    httphandler.send_response(200)
    httphandler.send_header("Content-type", "text/plain")
    httphandler.end_headers()
    
    manager_obj = manager.manager()

    completed_jobs = manager_obj.get_completed_jobs()
    running_jobs = manager_obj.get_running_jobs()
    queued_jobs = manager_obj.get_queued_jobs()


    all_jobs = {
        "completed_jobs": json.dumps([obj.get_info_dict() for obj in completed_jobs]),
        "running_jobs": json.dumps([obj.get_info_dict() for obj in running_jobs]),
        "queued_jobs": json.dumps([obj.get_info_dict() for obj in queued_jobs])
    }

    jobs = json.dumps(all_jobs)

    wr = webresponse(webstatus.SUCCESS, jobs)
    httphandler.wfile.write(bytes(wr.json_str(), "utf-8"))


#
# Gets a list of all available packages
#
# ENDPOINT /?get=packagelist (GET)
def get_endpoint_json_pkglist(httphandler):
    httphandler.send_response(200)
    httphandler.send_header("Content-type", "text/plain")
    httphandler.end_headers()
    
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
            "url": url
        }

        dict_arr.append(_dict)

    wr = webresponse(webstatus.SUCCESS, json.dumps(dict_arr))
    httphandler.wfile.write(bytes(wr.json_str(), "utf-8"))

#
# Gets a list of all available package builds
#
# ENDPOINT /?get=jsonpackagebuildlist (GET)
def get_endpoint_json_pkgbuildlist(httphandler):
    httphandler.send_response(200)
    httphandler.send_header("Content-type", "text/plain")
    httphandler.end_headers()

    stor = pkgbuildstorage.storage()
    pkgs = stor.packages
   
    json_pkgs = json.dumps(pkgs)

    wr = webresponse(webstatus.SUCCESS, json_pkgs)
    httphandler.wfile.write(bytes(wr.json_str(), "utf-8"))

#
# Endpoint specifically for leaf
# returns non-json response
#
# fetches package list in csv format
#
# ENDPOINT: /?get=packagelist (GET)
def get_endpoint_pkglist(httphandler):
    httphandler.send_response(200)
    httphandler.send_header("Content-type", "text/plain")
    httphandler.end_headers()
    
    stor = packagestorage.storage()
    meta_inf = stor.get_all_package_meta()
    req_line = httphandler.headers._headers[0][1]
    
    for meta in meta_inf:
        real_version = meta.get_latest_real_version()
        url = "http://{}/?get=package&pkgname={}".format(req_line, meta.get_name())

        httphandler.wfile.write(bytes("{};{};{};{};{};{}\n".format(meta.get_name(), real_version, meta.get_version(real_version), meta.get_description(), meta.get_dependencies(real_version), url), "utf-8"))

#
# Endpoint specifically for leaf.
# returns non-json response
#
# fetches a package file
#
# ENDPOINT: /?get=package (GET)
def get_endpoint_package(httphandler, form_data):
    stor = packagestorage.storage()
    
    package_file = None

    form_keys = form_data.keys()
    if("pkgname" in form_keys):
        
        # Package exists
        if(form_data["pkgname"] in stor.packages):
        
            # We have a version tag, get specific version.
            if("version" in form_keys):
                package_file = stor.get_pkg_path(form_data["pkgname"], form_data["version"])
                
                # Could not find specified version, notify failure.
                if(package_file is None):
                    httputils.send_error_response(httphandler, 404, "E_VERSION")
                    return


            # No version tag, get latest
            else:
                # latest version, no version tag
                meta = stor.get_meta_by_name(form_data["pkgname"])
                latest_version = meta.get_latest_real_version()
                package_file = stor.get_pkg_path(form_data["pkgname"], latest_version)
    
                # Could not find latest version (Shouldn't happen..?), notify failure.
                if(package_file is None):
                    httputils.send_error_response(httphandler, 404, "E_VERSION")
                    return 


        # Package doesn't exist, notify failure
        else:
            httputils.send_error_response(httphandler, 404, "E_PACKAGE")
            return

    # No package name specified, notify failure
    else:
        httputils.send_error_response(httphandler, 400, "E_PKGNAME")
        return
    
    # Couldn't find package file..
    if(package_file is None):
        httputils.send_error_response(httphandler, 404, "E_PACKAGE")
        return

    pfile = open(package_file, "rb")
    httputils.send_file(httphandler, pfile, os.path.getsize(package_file))

#
# Endpoint specifically for leaf.
# (returns non-json response)
#
# gets a list of all available versions;real_versions 
# for a given package
#
# ENDPOINT: /?get=versions (GET)
def get_endpoint_versions(httphandler, form_data):
    stor = packagestorage.storage()
    form_keys = form_data.keys()
    
    if(not "pkgname" in form_keys):
        httputils.send_error_response(httphandler, 400, "E_PKGNAME")
        return

    if(not form_data["pkgname"] in stor.packages):
        httputils.send_error_response(httphandler, 404, "E_PACKAGE")
        return

    meta = stor.get_meta_by_name(form_data["pkgname"])
    versions = meta.get_version_dict()

    httphandler.send_response(200)
    httphandler.send_header("Content-type", "text/plain")
    httphandler.end_headers()

    for key in versions:
        httphandler.wfile.write(bytes("{};{}\n".format(key, versions[key]), "utf-8")) 

#
# / endpoint, returns html page
#
# ENDPOINT: / (GET)
def root_endpoint(httphandler, form_data):
    httphandler.send_response(200)
    httphandler.send_header("Content-type", "text/html")
    httphandler.end_headers()

    httphandler.wfile.write(bytes("<html>", "utf-8"))
    httphandler.wfile.write(bytes("<h1>Nope.</h1>", "utf-8"))
    httphandler.wfile.write(bytes("</html>", "utf-8"))

#
# simple get-test endpoint
#
# ENDPOINT: /test (GET)
def test_endpoint(httphandler, form_data):
    httphandler.send_response(200)
    httphandler.send_header("Content-type", "text/html")
    print(httphandler.headers._headers[0][1])
    httphandler.end_headers()

    httphandler.wfile.write(bytes("<html>", "utf-8"))
    httphandler.wfile.write(bytes("<h1> Request acknowledged. </h1>", "utf-8"))
    httphandler.wfile.write(bytes("<p> Request: {} </p>".format(form_data), "utf-8"))
    httphandler.wfile.write(bytes("</html>", "utf-8"))

