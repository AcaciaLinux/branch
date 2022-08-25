import os
import json

from log import blog
from package import build

class storage():

    def __init__(self):
        if(not os.path.exists("./packagebuilds/")):
            os.mkdir("./packagebuilds/")

        # index local storage on init
        blog.debug("Indexing local storage..")
        self.packages = [ ]
        pkg_num = self.index()
        blog.debug("Found {} package(s)!".format(pkg_num))
    
    #
    # index the package build storage
    #
    def index(self):
        # reset packagebuild list
        self.packages = [ ]

        dirs = [ f.path for f in os.scandir("./packagebuilds") if f.is_dir() ]
        for dir in dirs:
            if(os.path.exists(os.path.join(dir, "package.bpb"))):
                pkg_name = os.path.basename(os.path.normpath(dir))
                self.packages.append(pkg_name)
        
        return len(self.packages)

    #
    # get a package build file from localstorage
    #
    def get_pkg_build_file(self, name):
        return os.path.join(os.path.join("./packagebuilds/", name), "package.bpb")

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
    # create a storage directory for a packagebuild 
    #
    def create_stor_directory(self, name):
        pkgs_dir = os.path.join(os.getcwd(), "./packagebuilds")
        pkg_dir = os.path.join(pkgs_dir, name)

        if(not os.path.exists(pkg_dir)):
            os.mkdir(pkg_dir)

        return pkg_dir
