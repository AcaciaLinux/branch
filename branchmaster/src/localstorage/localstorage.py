
import os
from log import blog
from localstorage import build
import json

class storage():
    packages = [ ]

    def __init__(self):
        blog.debug("Indexing local storage..")
        pkg_num = self.index()
        blog.debug("Found {} package(s)!".format(pkg_num))
    
    def index(self):
        self.packages = [ ]


        packages = [ ]
        dirs = [ f.path for f in os.scandir("./pkgs") if f.is_dir() ]
        for dir in dirs:
            if(os.path.exists(os.path.join(dir, "package.bpb"))):
                pkg_name = os.path.basename(os.path.normpath(dir))
                self.packages.append(pkg_name)
        
        return len(self.packages)

    def get_pkg_build_file(self, name):
        return os.path.join(os.path.join("./pkgs/", name), "package.bpb")

    def get_json_bpb(self, name):
        # check if package exists
        if(not name in self.packages):
            return None

        pkg_path = self.get_pkg_build_file(name)
        bpb = build.parse_build_file(pkg_path)
        bpb_json = build.pack_json(bpb)
        
        return bpb_json

    def get_bpb_obj(self, name):
        # check if package exists
        if(not name in self.packages):
            return None

        pkg_path = self.get_pkg_build_file(name)
        bpb = build.parse_build_file(pkg_path)
        return bpb

def check_storage():
    if(not os.path.exists("./pkgs")):
        blog.info("Creating local package directory")
        os.mkdir("./pkgs")
