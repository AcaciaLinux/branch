from webserver import webserver
from webserver import httputils
from localstorage import packagestorage

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
    elif(form_data["get"] == "package"):
        get_endpoint_package(httphandler, form_data)
    else:
        httputils.generic_malformed_request(httphandler)

def get_endpoint_pkglist(httphandler):
    httphandler.send_response(200)
    httphandler.send_header("Content-type", "text/plain")
    httphandler.end_headers()
    
    stor = packagestorage.storage()
    meta_inf = stor.get_all_package_meta()

    for meta in meta_inf:
        real_version = meta.get_latest_real_version()
        url = "http://localhost:8080/?get=package&pkgname={}".format(meta.get_name())

        httphandler.wfile.write(bytes("{};{};{};{};{};{}\n".format(meta.get_name(), real_version, meta.get_version(real_version), meta.get_description(), meta.get_dependencies(real_version), url), "utf-8"))

def get_endpoint_package(httphandler, form_data):
    httphandler.send_response(200)
    httphandler.send_header("Content-type", "text/plain")
    httphandler.end_headers()

    stor = packagestorage.storage()
    
    package_file = None

    form_keys = form_data.keys()
    if("pkgname" in form_keys):
        
        # Package exists
        if(form_data["pkgname"] in stor.packages):
        
            # We have a version tag, get specific version.
            if("version" in form_keys):
                package_file = stor.get_pkg_path(form_data["pkgname"], int(form_data["version"]))
                
                # Could not find specified version, notify failure.
                if(package_file is None):
                    pass


            # No version tag, get latest
            else:
                # latest version, no version tag
                meta = stor.get_meta_by_name(form_data["pkgname"])
                latest_version = meta.get_latest_real_version()
                package_file = stor.get_pkg_path(form_data["pkgname"], latest_version)
    
                # Could not find latest version (Shouldn't happen..?), notify failure.
                if(package_file is None):
                    pass
                


        # Package doesn't exist, notify failure
        else:
            pass
    
    # No package name specified, notify failure
    else:
        pass

    if(package_file is None):
        return


    pfile = open(package_file, "rb")
    httputils.send_file(httphandler, pfile)



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

