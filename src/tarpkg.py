import tarfile
import os
import lfpkg

def pack():
    if not("leaf.pkg" in os.listdir(os.getcwd())):
        print("This does not appear to be a package directory. Aborting.")
        exit(-1)
    
    leafpkg = lfpkg.parse("leaf.pkg")
    
    print("Creating lfpkg file for {}...".format(leafpkg.name))

    pwd = os.path.abspath(os.path.join(os.getcwd(), os.pardir))
    tar_name = "{}-{}.lfpkg".format(leafpkg.name, leafpkg.version)
    pkg_file_tar_gz = tarfile.open(os.path.join(pwd, tar_name), "w:gz")

    for root, dirs, files in os.walk(os.getcwd()):
        for file in files:
            print("Adding to tarfile: {}".format(file))
            pkg_file_tar_gz.add(os.path.join(root, file), os.path.relpath(os.path.join(root, file), os.path.join(os.getcwd(), '..')))
    pkg_file_tar_gz.close()

    print("Package file created in {}".format(pwd))

    
