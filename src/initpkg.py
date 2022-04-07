import os

def newpkg():
    print("Initializing empty package directory.")
    print("Package name: ")
    pkg_name = input()

    print("Package version: ")
    pkg_version = input()

    print("Package description: ")
    pkg_desc = input()

    print("Package dependencies ([pkg1][pkg2][pkg3]): ")
    pkg_deps = input()

    pkg_dir = "{}-{}".format(pkg_name, pkg_version)
    pkg_path = os.path.join(os.getcwd(), pkg_dir)

    # create pkg dir
    try:
        os.mkdir(pkg_path)
    except FileExistsError:
        print("Package directory exists. Did you already create it?")
        exit(-1)

    #create data subdir
    os.mkdir(os.path.join(pkg_path, "data"))

    leaf_pf = open(os.path.join(pkg_path, "leaf.pkg"), "w")
    leaf_pf.write("name={}\n".format(pkg_name))
    leaf_pf.write("version={}\n".format(pkg_version))
    leaf_pf.write("description={}\n".format(pkg_desc))
    leaf_pf.write("dependencies={}\n".format(pkg_deps))
    
    print("Package {} created.".format(pkg_name))

