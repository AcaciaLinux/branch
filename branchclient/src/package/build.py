import os
import shutil
import json
import blog

class package_build():
    def __init__(self):
        self.name = ""
        self.version = ""
        self.real_version = ""
        self.dependencies = ""
        self.build_dependencies = ""
        self.cross_dependencies = ""
        self.source = ""
        self.extra_sources = [ ]
        self.description = ""
        self.build_script = [ ]

    def get_json(self):
        return json.dumps(self.__dict__)

#
# parse json pkgbuild
#
def parse_build_json(json_obj):
    pkgbuild = package_build()

    pkgbuild.name = json_obj['name']
    pkgbuild.real_version = json_obj['real_version']
    pkgbuild.version = json_obj['version']
    pkgbuild.source = json_obj['source']
    pkgbuild.extra_sources = json_obj['extra_sources']
    pkgbuild.description = json_obj['description']
    pkgbuild.dependencies = json_obj['dependencies']
    pkgbuild.build_dependencies = json_obj['build_dependencies']
    pkgbuild.cross_dependencies = json_obj['cross_dependencies']
    pkgbuild.build_script = json_obj['build_script']
    return pkgbuild
    
#
# parse a build file
#
def parse_build_file(pkg_file):
    if(not os.path.exists(pkg_file)):
        blog.error("This does not appear to be a package directory.")
        return -1

    build_file = open(pkg_file, "r")
    build_arr = build_file.read().split("\n")

    pkgbuild = package_build()

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

            pkgbuild.build_script.append(prop)
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
                pkgbuild.name = val
            elif(key == "version"):
                pkgbuild.version = val
            elif(key == "real_version"):
                pkgbuild.real_version = val
            elif(key == "source"):
                pkgbuild.source = val
            elif(key == "extra_sources"):
                pkgbuild.extra_sources = parse_bpb_str_array(val) 
            elif(key == "dependencies"):
                pkgbuild.dependencies = val
            elif(key == "description"):
                pkgbuild.description = val
            elif(key == "builddeps"):
                pkgbuild.build_dependencies = val
            elif(key == "crossdeps"):
                pkgbuild.cross_dependencies = val
            elif(key == "build"):
                build_opts = True
   
    return pkgbuild

#
# Parses branchpackagebuild array formay:
# [a][b][c]
#
def parse_bpb_str_array(string):
    vals = [ ]
    buff = ""

    for c in string:
        if(c == ']'):
            vals.append(buff)
            buff = ""
        elif(not c == '['):
            buff = buff + c
    
    blog.debug("Parsed values: {}".format(vals))
    return vals

#
# creates a pkgbuild directory
#
def create_pkg_workdir(pkg_opts):
    if(os.path.exists(pkg_opts.name)):
        blog.warn("Overwriting local version of package build with checked out version..")
        shutil.rmtree(pkg_opts.name)

    os.mkdir(pkg_opts.name)
    wkdir = os.path.join(os.getcwd(), pkg_opts.name)
    pkg_file = os.path.join(wkdir, "package.bpb")
    write_build_file(pkg_file, pkg_opts)


#
# write build file to disk
#
def write_build_file(file, pkg_opts):
    bpb_file = open(file, "w")
    bpb_file.write("name={}\n".format(pkg_opts.name))
    bpb_file.write("version={}\n".format(pkg_opts.version))
    bpb_file.write("real_version={}\n".format(pkg_opts.real_version))
    bpb_file.write("source={}\n".format(pkg_opts.source))

    # write extra_sources array in bpb format
    bpb_file.write("extra_sources=")
    
    for exs in pkg_opts.extra_sources:
        bpb_file.write("[{}]".format(exs))

    bpb_file.write("\n")

    bpb_file.write("dependencies={}\n".format(pkg_opts.dependencies))
    bpb_file.write("builddeps={}\n".format(pkg_opts.build_dependencies))
    bpb_file.write("crossdeps={}\n".format(pkg_opts.cross_dependencies))
    bpb_file.write("description={}\n".format(pkg_opts.description))
    bpb_file.write("build={\n")
    
    for line in pkg_opts.build_script:
        bpb_file.write("\t")
        bpb_file.write(line)
        bpb_file.write("\n")

    bpb_file.write("}")


#
#
#
