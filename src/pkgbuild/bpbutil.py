from log import blog
import os

#Creates a branch package build file.
def createbpb():
    if("leaf.pkg" in os.listdir(os.getcwd())):
        blog.info("This appears to be a package directory. Aborting.")
        exit(-1)

    if("package.bpb" in os.listdir(os.getcwd())):
        blog.info("This directory already contains a package build file. Aborting.")
        exit(-1)

    print("Package name:")
    pkg_name = input()

    print("Package version:")
    pkg_version = input()

    print("Package description:")
    pkg_des = input()

    print("Package source:")
    pkg_src = input()

    print("Package runtime dependencies: [pkg1][pkg2][pkg3]")
    pkg_deps = input()

    print("Package buildtime dependencies: [pkg1][pkg2][pkg3]")
    pkg_builddeps = input()

    bpb_file = open("package.bpb", "w")
    bpb_file.write("name={}\n".format(pkg_name))
    bpb_file.write("version={}\n".format(pkg_version))
    bpb_file.write("source={}\n".format(pkg_src))
    bpb_file.write("dependencies={}\n".format(pkg_deps))
    bpb_file.write("builddeps={}\n".format(pkg_builddeps))
    bpb_file.write("description={}\n".format(pkg_des))
    bpb_file.write('''build={}''')

    blog.info("package.bpb created!")
