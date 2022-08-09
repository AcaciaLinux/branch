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
    
