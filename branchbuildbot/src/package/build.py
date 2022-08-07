import tarfile
import os
import subprocess
import shutil
import requests
import tarfile
import json

from buildenvmanager import buildenv
from log import blog
from package import leafpkg

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


def build(directory, package_build):
    # directory we were called in, return after func returns
    call_dir = os.getcwd()

    # change to packagebuild directory
    os.chdir(directory)
    
    # create build_dir
    build_dir = os.path.join(directory, "build")
    os.mkdir(build_dir)

    # get leafpkg
    lfpkg = leafpkg.leafpkg()
    lfpkg.name = package_build.name
    lfpkg.version = package_build.version
    lfpkg.real_version = package_build.real_version
    lfpkg.description = package_build.description
    lfpkg.dependencies = package_build.dependencies
    
    # write leafpkg to disk
    destdir = leafpkg.write_leaf_package_directory(lfpkg)
   
    # change to build directory
    os.chdir(build_dir)
    
    if(package_build.source):
        try:
            source_request = requests.get(package_build.source, stream=True)
            source_file = package_build.source.split("/")[-1]

            # fetch sources
            blog.info("Fetching source: " + source_file)
            out_file = open(source_file, "wb")
            shutil.copyfileobj(source_request.raw, out_file)

            # check if file is tarfile and extract if it is
            if(tarfile.is_tarfile(source_file)):
                blog.info("Source is a tar file. Extracting...")
                tar_file = tarfile.open(source_file, "r")
                tar_obj = tar_file.extractall(".")
            
            # TODO: check for zip

            else:
                blog.warn("Source is not a tar file. Manual extraction required in build script..")

            blog.info("Source fetched")
        except Exception:
            blog.error("Broken link in packagebuild. Not fetching source.")
    else:
        blog.warn("No source specified. Not fetching source.") 
   
    blog.info("Installing dependencies to temproot..")
    buildenv.install_pkgs(get_pkg_array(package_build.dependencies))
    buildenv.install_pkgs(get_pkg_array(package_build.dependencies))


    print("====================================================")
    blog.info("Package build will run in: {}".format(build_dir))
    blog.info("Package destination is: {}".format(destdir))
    
    blog.info("Writing build script to disk..")
    build_sh = open(os.path.join(build_dir, "build.sh"), "w")
    build_sh.write("set +e\n")

    for line in package_build.build_script:
        build_sh.write(line)
        build_sh.write("\n")

    build_sh.write("set -e\n")
    build_sh.close()

    temp_root = buildenv.get_build_path()
    
    chroot_destdir = destdir.replace(temp_root, "")

    # entry script
    entry_sh_path = os.path.join(temp_root, "entry.sh")
    entry_sh = open(entry_sh_path, "w")

    entry_sh.write("cd /branchbuild/build && PKG_INSTALL_DIR={} ./build.sh\n".format(chroot_destdir))
    entry_sh.close()

    # set executable bit on scripts
    os.system("chmod +x build.sh")
    os.system("chmod +x {}".format(entry_sh_path))

    blog.info("Chrooting to build environment...")
    blog.info("Build started on ..")


    proc = subprocess.run(["chroot", temp_root, "bash", "/entry.sh"])

    print("====================================================")
    if(proc.returncode != 0):
        blog.error("Package build script failed.")
        os.chdir(call_dir)
        return "BUILD_FAILED"

    blog.info("Build completed successfully.")

    # change back to call_dir
    os.chdir(call_dir)

    return "BUILD_COMPLETE"

def get_pkg_array(string):
    deps = [ ]
    buff = ""

    for c in string:
        if(c == ']'):
            deps.append(buff)
            buff = ""
        elif(not c == '['):
            buff = buff + c

    return deps

def json_get_key(json_obj, key):
    try:
        return json_obj[key]
    except KeyError:
        return "UNSET"

def parse_build_json(json):
    BPBopts = BPBOpts()

    BPBopts.name = json_get_key(json, "name")
    BPBopts.real_version = json_get_key(json, "real_version")
    BPBopts.version = json_get_key(json, "version")
    BPBopts.source = json_get_key(json, "source")
    BPBopts.description = json_get_key(json, "description")
    BPBopts.dependencies = json_get_key(json, "dependencies")
    BPBopts.build_dependencies = json_get_key(json, "build_dependencies")
    BPBopts.build_script = json_get_key(json, "build_script")

    return BPBopts
    

def parse_build_file(pkg_file):
    build_file = open(pkg_file, "r")
    build_arr = build_file.read().split("\n")

    BPBopts = BPBOpts()

    BPBopts.name = "UNSET"
    BPBopts.version = "UNSET"
    BPBopts.real_version = "UNSET"
    BPBopts.source = "UNSET"
    BPBopts.dependencies = "UNSET"
    BPBopts.description =  "UNSET"
    BPBopts.build_dependencies = "UNSET"

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
                return -1

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

