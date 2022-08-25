import tarfile
import os

from log import blog

class leafpkg():
    def __init__(self):
        self.name = ""
        self.version = ""
        self.real_version = ""
        self.description = ""
        self.dependencies = ""

def parse_leaf_package(pkg_file_path):
    lfpkg_file = open(pkgFile_path, "r")
    lfpkg_arr = lfpkg_file.read().split("\n")

    leafpkg = lfpkg()

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
        elif(key == "real_version"):
            leafpkg.real_version = val
        elif(key == "description"):
            leafpkg.description = val
        elif(key == "dependencies"):
            leafpkg.dependencies = val

    return leafpkg

def write_leaf_package_directory(package):
    blog.info("Initializing empty package directory.")
    pkg_dir = "{}-{}".format(package.name, package.version)
    pkg_path = os.path.join(os.getcwd(), pkg_dir)

    # create pkg dir
    try:
        os.mkdir(pkg_path)
    except FileExistsError:
        shutil.rmtree(pkg_path)
        os.mkdir(pkg_path)

    #create data subdir
    os.mkdir(os.path.join(pkg_path, "data"))

    leaf_pf = open(os.path.join(pkg_path, "leaf.pkg"), "w")
    leaf_pf.write("name={}\n".format(package.name))
    leaf_pf.write("version={}\n".format(package.version))
    leaf_pf.write("real_version={}\n".format(package.real_version))
    leaf_pf.write("description={}\n".format(package.description))
    leaf_pf.write("dependencies={}\n".format(package.dependencies))

    blog.info("Package {} created.".format(package.name))
    return os.path.join(pkg_path, "data")

def create_tar_package(package_directory, package):
    pkg_name = "{}-{}".format(package.name, package.version)
    tar_name = "{}.lfpkg".format(pkg_name)
    pkg_file_tar = tarfile.open(os.path.join(package_directory, tar_name), "w:xz")
    
    leafpkg_dir = os.path.join(package_directory, pkg_name)
    for root, dirs, files in os.walk(leafpkg_dir, followlinks=False):
        for file in files:
            blog.info("Adding file: {}".format(os.path.join(root, file)))
            pkg_file_tar.add(os.path.join(root, file), os.path.relpath(os.path.join(root, file), os.path.join(leafpkg_dir, '..')))
        for dir in dirs:
            if (len(os.listdir(os.path.join(root, dir))) == 0):
                blog.info("Adding dir: {}".format(os.path.join(root, dir)))
                pkg_file_tar.add(os.path.join(root, dir), os.path.relpath(os.path.join(root, dir), os.path.join(leafpkg_dir, '..')))
            elif (os.path.islink(os.path.join(root, dir))):
                blog.info("Adding dirlink: {}".format(os.path.join(root, dir)))
                pkg_file_tar.add(os.path.join(root, dir), os.path.relpath(os.path.join(root, dir), os.path.join(leafpkg_dir, '..')))

    pkg_file_tar.close()
    blog.info("Package file created in {}".format(package_directory))
    return os.path.join(package_directory, tar_name)
