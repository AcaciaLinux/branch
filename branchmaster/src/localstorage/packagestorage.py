PACKAGE_DIRECTORY = "./packages/"

import os
import json

from log import blog

class branch_meta():

    def __init__(self):
        self.name = ""
        self.description = ""
        
        self.versions = { }
        self.version_dependencies = { }
    
    def read_file(self, file):
        file = open(file, 'r')
        json_obj = json.load(file)
        
        self.name = json_obj['name']
        self.description = json_obj['description']
        self.versions = json_obj['versions']
        self.version_dependencies = json_obj['version_dependencies']

    def write_file(self, file):
        json_obj = json.dumps(self.__dict__, indent=4)

        file = open(file, "w")
        file.write(json_obj)
    
    def get_name(self):
        return self.name

    def get_description(self):
        return self.description

    def get_latest_real_version(self):
        return max(self.versions) 

    def get_version(self, real_version):
        return self.versions[real_version]

    def get_dependencies(self, real_version):
        return self.version_dependencies[real_version]

    def get_version_dict(self):
        return self.versions

class storage():

    packages = [ ]

    def __init__(self):
        if(not os.path.exists(PACKAGE_DIRECTORY)):
            os.mkdir("packages")

        self.index()

    #
    # index the package build storage
    #
    def index(self):
        # reset packagebuild list
        self.packages = [ ]

        dirs = [ f.path for f in os.scandir(PACKAGE_DIRECTORY) if f.is_dir() ]
        for dir in dirs:
            if(os.path.exists(os.path.join(dir, "branch.meta"))):
                pkg_name = os.path.basename(os.path.normpath(dir))
                self.packages.append(pkg_name)
        
        return len(self.packages)
    
    def get_packages_array(self):
        return self.packages
    
    #
    # Sets up the necessary package directories
    # and creates the branch meta file
    # Returns the target path for the package.
    #
    def add_package(self, package_build):
        pkg_root = os.path.join(PACKAGE_DIRECTORY, package_build.name)
    
        meta_file = os.path.join(pkg_root, "branch.meta")
    
        pkg_target_dir = os.path.join(pkg_root, package_build.real_version)
        package = os.path.join(pkg_target_dir, "{}.lfpkg".format(package_build.name))

        # root doesn't exist, new package
        if(not os.path.exists(pkg_root)):
            os.mkdir(pkg_root)
            
            meta = branch_meta()
            meta.name = package_build.name
            meta.description = package_build.description
            meta.versions[package_build.real_version] = package_build.version
            meta.version_dependencies[package_build.real_version] = package_build.dependencies
            meta.write_file(meta_file)

            os.mkdir(pkg_target_dir)
        
        # root already exists
        else:
            # version already set, no update needed.
            if(os.path.exists(pkg_target_dir)):
                blog.info("Package already exists. Assuming minor update..")
                try:
                    os.remove(package)
                except Exception:
                    blog.debug("Couldn't delete.")

            # new version but package exists
            else:
                os.mkdir(pkg_target_dir)

            # update meta
            meta = branch_meta()
            meta.read_file(meta_file)
            meta.name = package_build.name
            meta.description = package_build.description
            meta.versions[package_build.real_version] = package_build.version
            meta.version_dependencies[package_build.real_version] = package_build.dependencies
            meta.write_file(meta_file)

        self.index()
        return package

    #
    # Get meta information for a package
    #
    def get_meta_by_name(self, package_name):
        if(package_name in self.packages):
            pkg_path = os.path.join(PACKAGE_DIRECTORY, package_name)
            meta_file = os.path.join(pkg_path, "branch.meta")

            meta = branch_meta()
            meta.read_file(meta_file)
            return meta
        else:
            return None

    #
    # Get all package meta files
    #
    def get_all_package_meta(self):
        pkg_meta = [ ]

        for package in self.packages:
            pkg_path = os.path.join(PACKAGE_DIRECTORY, package)
            meta_file = os.path.join(pkg_path, "branch.meta")

            meta = branch_meta()
            meta.read_file(meta_file)
            pkg_meta.append(meta)

        return pkg_meta
     
    #
    # Get package by name and version
    #
    def get_pkg_path(self, name, real_version):
        pkg_root = os.path.join(PACKAGE_DIRECTORY, name)
        if(not os.path.exists(pkg_root)):
            return None

        pkg_version_path = os.path.join(pkg_root, real_version)
        if(not os.path.exists(pkg_version_path)):
            return None
        
        pkg_file = os.path.join(pkg_version_path, "{}.lfpkg".format(name))
        if(not os.path.exists(pkg_file)):
            return None

        return pkg_file
        


