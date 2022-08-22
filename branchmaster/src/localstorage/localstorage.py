
import os
from log import blog
from package import build
import json

class storage():
    # static package object
    packages = [ ]

    def __init__(self):
        # index local storage on init
        blog.debug("Indexing local storage..")
        pkg_num = self.index()
        blog.debug("Found {} package(s)!".format(pkg_num))
    
    #
    # index the package build storage
    #
    def index(self):
        # reset packagebuild list
        self.packages = [ ]

        dirs = [ f.path for f in os.scandir("./pkgs") if f.is_dir() ]
        for dir in dirs:
            if(os.path.exists(os.path.join(dir, "package.bpb"))):
                pkg_name = os.path.basename(os.path.normpath(dir))
                self.packages.append(pkg_name)
        
        return len(self.packages)

    #
    # get a package build file from localstorage
    #
    def get_pkg_build_file(self, name):
        return os.path.join(os.path.join("./pkgs/", name), "package.bpb")

    #
    # get package build by name from localstorage
    #
    def get_json_bpb(self, name):
        # check if package exists
        if(not name in self.packages):
            return None

        pkg_path = self.get_pkg_build_file(name)
        bpb = build.parse_build_file(pkg_path)
        bpb_json = bpb.get_json()
        
        return bpb_json

    #
    # get a Package build object by name from localstorage
    #
    def get_bpb_obj(self, name):
        # check if package exists
        if(not name in self.packages):
            return None

        pkg_path = self.get_pkg_build_file(name)
        bpb = build.parse_build_file(pkg_path)
        return bpb

#
# Check if ./pkgs directory exists, create if it doesn't
#
def check_storage():
    if(not os.path.exists("./pkgs")):
        blog.info("Creating local package directory")
        os.mkdir("./pkgs")
