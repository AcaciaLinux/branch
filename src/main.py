import os
import tarfile

def main():
    print("Branch - The AcaciaLinux packager")

    # CHECK IF SHELL ENV VARIABLE IS SET
    shell = "/bin/bash"
    if("BSHELL" in os.environ):
        shell = os.environ.get("BSHELL")

    # GET PACKAGE NAME/VERSION FROM STDIN
    print("[*] Enter a package name: ")
    pkg_name = input()
    print("[*] Enter a package version: ")
    pkg_vers = input()

    # PKG DIR 
    pkg_sub_dir = "{}-{}".format(pkg_name, pkg_vers)
    pkg_work_dir = ""
    
    # good idea? might remove later...
    # ASK USER FOR PKG WORK DIR
    print("[*] Would you like to create the pkg work directory in cwd? (y/n)")
    answ = input()
    if(answ == "y"):
        pkg_work_dir = os.path.join(os.getcwd(), pkg_sub_dir)
    elif(answ == "n"):
        print("[*] Enter workdirectory.. e.g: /packages/")
        pkg_work_dir = input()
    else:
        print("[!] Invalid answer.")
        exit(-1)

    # CREATE PKG WORK DIR
    print("[*] Creating pkg work directory at {}..".format(pkg_work_dir))
    try:
        os.mkdir(pkg_work_dir)
    except FileExistsError:
        print("[*] Package directory already exists. Choose a different package directory.")
        exit(-1)
    
    # CREATE DATA SUBDIR
    print("[*] Creating data directory")
    os.mkdir(os.path.join(pkg_work_dir, "data"))

    # ENTER SHELL
    print("[!!] Your pkg work directory is: ", pkg_work_dir)
    print("[!!] Set package DESTDIR to ", os.path.join(pkg_work_dir, "data"))
    print("[!!] Entering shell..")
    print("[!!] Exit shell once you are done installing files to pkg data directory")
    os.system(shell)

    # FILE LIST
    print("[*] Creating package file..") 
    filelist = []
    for root, dirs, files in os.walk(os.path.join(pkg_work_dir, "data"), topdown=True):
        for file in files:
            filelist.append(os.path.join(root, file))
    
    # OPEN AND WRITE OPTIONS TO LEAFPKG FILE
    leaf_pkg_file = open(os.path.join(pkg_work_dir, "leaf.pkg"), "w")
    leaf_pkg_file.write("name={}\n".format(pkg_name))    
    leaf_pkg_file.write("version={}\n".format(pkg_vers))
    leaf_pkg_file.write("files=")
   
    # ADD FILELIST
    for file in filelist:
        leaf_pkg_file.write("[{}]".format(os.path.relpath(file, os.path.join(pkg_work_dir, "data"))))
    leaf_pkg_file.write("\n")

    # ASK FOR DEPENDENCIES
    print("[*] Enter dependency string: [a][b][c][d]")
    dependencies = input()
    leaf_pkg_file.write("dependencies={}".format(dependencies))
    leaf_pkg_file.close()

    print("[*] Done creating leaf.pkg file")
    print("[*] Creating tar file..")

    # OPEN TAR FILE
    tar_name = "{}-{}.lfpkg".format(pkg_name, pkg_vers)
    pkg_file_tar_gz = tarfile.open(tar_name, "w")
    
    # CREATE TAR ARCHIVE
    for root, dirs, files in os.walk(pkg_work_dir):
        for file in files:
            print("[*] Adding to tar file: {} ".format(file))
            pkg_file_tar_gz.add(os.path.join(root, file), os.path.relpath(os.path.join(root, file), os.path.join(pkg_work_dir, '..')))
    pkg_file_tar_gz.close()
    
    print("[*] Done. Package file created: {}".format(tar_name))
    
if(__name__ == "__main__"):
    main()
