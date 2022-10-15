import json
import os

from webserver import webserver
from webserver import httputils
from localstorage import packagestorage
from config import config

class endpoint():
    def __init__(self, path, handler):
        self.path = path
        self.handlerfunc = handler

def register_endpoints():
    webserver.register_endpoint(endpoint("get", get_endpoint))
    webserver.register_endpoint(endpoint("", root_endpoint))
    webserver.register_endpoint(endpoint("test", test_endpoint))

def get_endpoint(httphandler, form_data):
    if(form_data["get"] == "packagelist"):
        get_endpoint_pkglist(httphandler)
    elif(form_data["get"] == "jsonpackagelist"):
        get_endpoint_json_pkglist(httphandler)
    elif(form_data["get"] == "package"):
        get_endpoint_package(httphandler, form_data)
    elif(form_data["get"] == "versions"):
        get_endpoint_versions(httphandler, form_data)
    else:
        httputils.generic_malformed_request(httphandler)

def get_jobs_endpoint(httphandler):
    httphandler.send_response(200)
    httphandler.send_header("Content-type", "text/plain")
    httphandler.end_headers()
    
    manager_obj = manager.manager()
    all_jobs = [ ]

    completed_jobs = manager.get_completed_jobs()
    running_jobs = manager.get_running_jobs()
    queued_jobs = manager.get_queued_jobs()

    all_jobs.append(completed_jobs)
    all_jobs.append(running_jobs)
    all_jobs.append(queued_jobs)

    httphandler.wfile.write(bytes(json.dumps([obj.get_info_dict() for obj in all_jobs]), "utf-8"))


def get_endpoint_pkglist(httphandler):
    httphandler.send_response(200)
    httphandler.send_header("Content-type", "text/plain")
    httphandler.end_headers()
    
    stor = packagestorage.storage()
    meta_inf = stor.get_all_package_meta()
    conf = config.branch_options()

    for meta in meta_inf:
        real_version = meta.get_latest_real_version()
        url = "http://{}:{}/?get=package&pkgname={}".format(conf.listenaddr, conf.httpport, meta.get_name())

        httphandler.wfile.write(bytes("{};{};{};{};{};{}\n".format(meta.get_name(), real_version, meta.get_version(real_version), meta.get_description(), meta.get_dependencies(real_version), url), "utf-8"))

def get_endpoint_json_pkglist(httphandler):
    httphandler.send_response(200)
    httphandler.send_header("Content-type", "text/plain")
    httphandler.end_headers()
    
    stor = packagestorage.storage()
    meta_inf = stor.get_all_package_meta()
    conf = config.branch_options()

    dict_arr = [ ]

    for meta in meta_inf:
        real_version = meta.get_latest_real_version()
        url = "http://{}:{}/?get=package&pkgname={}".format(conf.listenaddr, conf.httpport, meta.get_name())

        _dict = {
            "name" : meta.get_name(),
            "real_version": real_version,
            "version": meta.get_version(real_version),
            "description": meta.get_description(),
            "dependencies": meta.get_dependencies(real_version),
            "url": url
        }

        dict_arr.append(_dict)

    httphandler.wfile.write(bytes(json.dumps(dict_arr), "utf-8"))


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



def root_endpoint(httphandler, form_data):
    httphandler.send_response(200)
    httphandler.send_header("Content-type", "text/html")
    httphandler.end_headers()

    httphandler.wfile.write(bytes("<html>", "utf-8"))
    httphandler.wfile.write(bytes("<h1>Nope.</h1>", "utf-8"))
    httphandler.wfile.write(bytes("</html>", "utf-8"))


def test_endpoint(httphandler, form_data):
    httphandler.send_response(200)
    httphandler.send_header("Content-type", "text/html")
    httphandler.end_headers()

    httphandler.wfile.write(bytes("<html>", "utf-8"))
    httphandler.wfile.write(bytes("<h1> Request acknowledged. </h1>", "utf-8"))
    httphandler.wfile.write(bytes("<p> Request: {} </p>".format(form_data), "utf-8"))
    httphandler.wfile.write(bytes("</html>", "utf-8"))

