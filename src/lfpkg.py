import os

class lfpkg():
    def __init__(self, name, version, description, dependencies):
        self.name = name
        self.version = version
        self.description = description
        self.dependencies = dependencies

def parse():
    lfpkg_file = open("leaf.pkg", "r")
    lfpkg_arr = lfpkg_file.read().split()
    
    leafpkg = lfpkg("", "", "", "")

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
            
    return leafpkg
