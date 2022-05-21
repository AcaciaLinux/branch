import tarfile
import os
from leafpkg import lfpkg
from log import blog

def pack():
    if not("leaf.pkg" in os.listdir(os.getcwd())):
        blog.error("This does not appear to be a package directory. Aborting.")
        exit(-1)
    
    leafpkg = lfpkg.parse("leaf.pkg")

    blog.info("Creating lfpkg file for {}...".format(leafpkg.name))

    pwd = os.path.abspath(os.path.join(os.getcwd(), os.pardir))
    tar_name = "{}-{}.lfpkg".format(leafpkg.name, leafpkg.version)
    pkg_file_tar = tarfile.open(os.path.join(pwd, tar_name), "w:xz")

    for root, dirs, files in os.walk(os.getcwd(), followlinks=False):
        for file in files:
            blog.info("Adding file: {}".format(os.path.join(root, file)))
            pkg_file_tar.add(os.path.join(root, file), os.path.relpath(os.path.join(root, file), os.path.join(os.getcwd(), '..')))
        for dir in dirs:
            if (len(os.listdir(os.path.join(root, dir))) == 0):
                blog.info("Adding dir: {}".format(os.path.join(root, dir)))
                pkg_file_tar.add(os.path.join(root, dir), os.path.relpath(os.path.join(root, dir), os.path.join(os.getcwd(), '..')))
            elif (os.path.islink(os.path.join(root, dir))):
                blog.info("Adding dirlink: {}".format(os.path.join(root, dir)))
                pkg_file_tar.add(os.path.join(root, dir), os.path.relpath(os.path.join(root, dir), os.path.join(os.getcwd(), '..')))

    pkg_file_tar.close()
    blog.info("Package file created in {}".format(pwd))
