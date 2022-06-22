import os
from log import blog
from leafpkg import lfpkg 


#
# Initializes a new package directory
# returns 0, if already exists, otherwise rootpath
def newpkg(leafpkg):
    # create pkg dir
    try:
        os.mkdir(leafpkg.pkg_root)
    except FileExistsError:
        # package file already exists.
        return 0

    blog.info("Initializing new package directory..")

    #create data subdir
    os.mkdir(os.path.join(leafpkg.pkg_root, "data"))

    leaf_pf = open(os.path.join(leafpkg.pkg_root, "leaf.pkg"), "w")
    leaf_pf.write("name={}\n".format(leafpkg.name))
    leaf_pf.write("version={}\n".format(leafpkg.version))
    leaf_pf.write("description={}\n".format(leafpkg.description))
    leaf_pf.write("dependencies={}\n".format(leafpkg.dependencies))
    leaf_pf.write("pkgrel={}\n".format(leafpkg.real_version))

    return leafpkg.pkg_root

#
# Utility to create a leaf.pkg file
#
def pkg_utility():
    print("Package name: ")
    pkg_name = input()

    print("Package version: ")
    pkg_version = input()

    print("Package real version: (0 for the first version of the package)")
    pkg_rel = input()

    print("Package description: ")
    pkg_desc = input()

    print("Package dependencies ([pkg1][pkg2][pkg3]): ")
    pkg_deps = input()

    pkg_dir = "{}-{}".format(pkg_name, pkg_version)
    pkg_root = os.path.join(os.getcwd(), pkg_dir)

    return lfpkg.lfpkg(pkg_name, pkg_version, pkg_desc, pkg_deps, pkg_rel, pkg_root)
