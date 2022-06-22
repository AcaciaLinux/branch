import os

class lfpkg():
    def __init__(self, name, version, description, dependencies, real_version, pkg_root):
        self.name = name
        self.version = version
        self.description = description
        self.dependencies = dependencies
        self.real_version = real_version
        self.pkg_root = pkg_root

    def getDataPath(self):
        return "{}/data".format(self.pkg_root)

    def getPkgDirectory(self):
        return "{}-{}".format(self.name, self.version)

def parse(pkgFile_path):
    lfpkg_file = open(pkgFile_path, "r")
    lfpkg_arr = lfpkg_file.read().split("\n")
    
    leafpkg = lfpkg("", "", "", "", "", "")

    for prop in lfpkg_arr:
        prop_arr = prop.split("=")
        
        # Check if key has a value
        key = prop_arr[0]
        if(len(prop_arr) != 2):
            val = ""
        else:
            val = prop_arr[1]

        if(key == "name"):
            leafpkg.name = val
        elif(key == "version"):
            leafpkg.version = val
        elif(key == "description"):
            leafpkg.description = val
        elif(key == "dependencies"):
            leafpkg.dependencies = val
        elif(key == "pkgrel"):
            leafpkg.real_version

    return leafpkg
