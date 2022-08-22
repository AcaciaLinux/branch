import tarfile
import os
import subprocess
import shutil
import requests
import tarfile
import json

from log import blog

class BPBOpts():
    def __init__(self):
        self.name = ""
        self.version = ""
        self.dependencies = ""
        self.description = ""
        self.build_dependencies = ""
        self.build_script = [ ]

        self.job_id = "job"

    def get_json(self):
        return json.dumps(self.__dict__)

    def get_name_json(self):
        return {
            "pkg_name": self.name
        }

#
# get BPBopts object from json_object
#
def parse_build_json(json_obj):
    BPBopts = BPBOpts()

    try:
        BPBopts.name = json_obj['name']
        BPBopts.version = json_obj['version']
        BPBopts.source = json_obj['source']
        BPBopts.description = json_obj['description']
        BPBopts.dependencies = json_obj['dependencies']
        BPBopts.build_dependencies = json_obj['build_dependencies']
        BPBopts.build_script = json_obj['build_script']
    except KeyError:
        blog.debug("Client submitted invalid package build.")
        return None

    return BPBopts

#    
# parse build file from disk to BPBopts
#
def parse_build_file(pkg_file):
    build_file = open(pkg_file, "r")
    build_arr = build_file.read().split("\n")

    BPBopts = BPBOpts()

    build_opts = False
    command = ""
    for prop in build_arr:
        if(build_opts):
            if(prop == "}"):
                build_opts = False
                continue
            
            # remove tab indentation
            prop = prop.replace("\t", "")
            
            # skip empty lines
            if(len(prop) == 0):
                continue;

            BPBopts.build_script.append(prop)
        else:
            prop_arr = prop.split("=")
            key = prop_arr[0]

            if(len(key) == 0):
                continue

            if(len(prop_arr) != 2):
                blog.error("Broken package build file. Failed property of key: ", key)
                exit(-1)

            val = prop_arr[1]

            if(key == "name"):
                BPBopts.name = val
            elif(key == "version"):
                BPBopts.version = val
            elif(key == "source"):
                BPBopts.source = val
            elif(key == "dependencies"):
                BPBopts.dependencies = val
            elif(key == "description"):
                BPBopts.description = val
            elif(key == "builddeps"):
                BPBopts.build_dependencies = val
            elif(key == "build"):
                build_opts = True
   
    return BPBopts

#
# Create a storage directory for specified package in ./pkgs
#
def create_stor_directory(pkg_name):
    pkgs_dir = os.path.join(os.getcwd(), "./pkgs")
    pkg_dir = os.path.join(pkgs_dir, pkg_name)

    if(not os.path.exists(pkg_dir)):
        os.mkdir(pkg_dir)

    return pkg_dir

#
# Write build file from BPPopts to disk
#
def write_build_file(file, pkg_opts):
    bpb_file = open(file, "w")
    bpb_file.write("name={}\n".format(pkg_opts.name))
    bpb_file.write("version={}\n".format(pkg_opts.version))
    bpb_file.write("source={}\n".format(pkg_opts.source))
    bpb_file.write("dependencies={}\n".format(pkg_opts.dependencies))
    bpb_file.write("builddeps={}\n".format(pkg_opts.build_dependencies))
    bpb_file.write("description={}\n".format(pkg_opts.description))
    bpb_file.write("build={\n")
    
    for line in pkg_opts.build_script:
        bpb_file.write("\t")
        bpb_file.write(line)
        bpb_file.write("\n")

    bpb_file.write("}")
    blog.debug("package.bpb file written to disk.")
