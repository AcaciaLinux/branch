import os
import shutil
import json

from log import blog

class BPBOpts():
    def __init__(self):
        self.name = ""
        self.version = ""
        self.real_version = ""
        self.dependencies = ""
        self.description = ""
        self.build_dependencies = ""
        self.build_script = [ ]

        self.job_id = "job"

    def get_json(self):
        return json.dumps(self.__dict__)

def parse_build_json(json_obj):
    BPBopts = BPBOpts()

    BPBopts.name = json_obj['name']
    BPBopts.real_version = json_obj['real_version']
    BPBopts.version = json_obj['version']
    BPBopts.source = json_obj['source']
    BPBopts.description = json_obj['description']
    BPBopts.dependencies = json_obj['dependencies']
    BPBopts.build_dependencies = json_obj['build_dependencies']
    BPBopts.build_script = json_obj['build_script']

    return BPBopts
    

def parse_build_file(pkg_file):
    if(not os.path.exists(pkg_file)):
        blog.error("This does not appear to be a package directory.")
        return -1

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
                blog.error("Broken package build file. Failed property of key: {}".format(key))
                exit(-1)

            val = prop_arr[1]

            if(key == "name"):
                BPBopts.name = val
            elif(key == "version"):
                BPBopts.version = val
            elif(key == "real_version"):
                BPBopts.real_version = val
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

def create_pkg_workdir(pkg_opts):
    if(os.path.exists(pkg_opts.name)):
        blog.warn("Fetching latest version of pkgbuild..")
        shutil.rmtree(pkg_opts.name)

    os.mkdir(pkg_opts.name)
    wkdir = os.path.join(os.getcwd(), pkg_opts.name)
    pkg_file = os.path.join(wkdir, "package.bpb")
    write_build_file(pkg_file, pkg_opts)

def create_stor_directory(pkg_name):
    pkgs_dir = os.path.join(os.getcwd(), "./pkgs")
    pkg_dir = os.path.join(pkgs_dir, pkg_name)

    if(not os.path.exists(pkg_dir)):
        os.mkdir(pkg_dir)

    return pkg_dir

def write_build_file(file, pkg_opts):
    bpb_file = open(file, "w")
    bpb_file.write("name={}\n".format(pkg_opts.name))
    bpb_file.write("version={}\n".format(pkg_opts.version))
    bpb_file.write("real_version={}\n".format(pkg_opts.real_version))
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
    blog.info("package.bpb file written!")
