import os
import tarfile
import pysftp

def main():
    print("Branch - The AcaciaLinux packager")

    # CHECK IF SHELL ENV VARIABLE IS SET
    shell = "/bin/bash"
    if("BSHELL" in os.environ):
        shell = os.environ.get("BSHELL")


    # SFTP SUPPORT
    if("BSFTP" in os.environ):
        sftp = True

    # GET PACKAGE NAME/VERSION FROM STDIN
    print("[*] Enter a package name: ")
    pkg_name = input()
    print("[*] Enter a package version: ")
    pkg_vers = input()
    print("[*] Enter a package description: ")
    pkg_desc = input()

    # PKG DIR 
    pkg_sub_dir = "{}-{}".format(pkg_name, pkg_vers)
    pkg_work_dir = ""
    
    print("[*] Creating package directory in cwd")
    pkg_work_dir = os.path.join(os.getcwd(), pkg_sub_dir)

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
    leaf_pkg_file.write("description={}".format(pkg_desc))

    # ASK FOR DEPENDENCIES
    print("[*] Enter dependency string: [a][b][c][d]")
    dependencies = input()
    leaf_pkg_file.write("dependencies={}".format(dependencies))
    leaf_pkg_file.close()

    print("[*] Done creating leaf.pkg file")
    print("[*] Creating tar file..")

    # OPEN TAR FILE
    tar_name = "{}-{}.lfpkg".format(pkg_name, pkg_vers)
    pkg_file_tar_gz = tarfile.open(tar_name, "w:gz")
    
    # CREATE TAR ARCHIVE
    for root, dirs, files in os.walk(pkg_work_dir):
        for file in files:
            print("[*] Adding to tar file: {} ".format(file))
            pkg_file_tar_gz.add(os.path.join(root, file), os.path.relpath(os.path.join(root, file), os.path.join(pkg_work_dir, '..')))
    pkg_file_tar_gz.close()
    
    print("[*] Package file created: {}".format(tar_name))
    
    if(not "BSFTP" in os.environ):
        print("BSFTP variable is not set. Done!")
        exit(0)

    serv_ip = ""
    if(not "SERVIP" in os.environ):
        print("[!] SERVIP Environment variable required.")
        exit(-1)
    else:
        serv_ip = os.environ.get("SERVIP")
        

    sftp_con = pysftp.Connection(host=serv_ip, username="root", private_key="~/.ssh/id_rsa", private_key_pass="")
    print("[*] Connection to {} established.".format(serv_ip)) 
    print("[*] Changing directory to package dir")
    sftp_con.cwd("/var/www/html/packages/")

    print("[*] mkdir package subdir")
    pkg_dir = pkg_name
    sftp_con.mkdir(pkg_dir)
    
    print("[*] cd package subdir")
    sftp_con.cwd(pkg_dir)

    print("[*] Uploading package..")
    sftp_con.put(tar_name)
    print("[*] Upload completed..")

    print("[*] Fetching leaf.pkglist")
    sftp_con.cwd("..")
    sftp_con.get("leaf.pkglist")

    print("[*] Appending package to pkglist...")
    leaf_pkg_list = open("leaf.pkglist", "a")
    
    print("[*] Appending package string to leaf.pkglist")
    url = "http://{}/packages/{}/{}".format(serv_ip, pkg_dir, tar_name)
    leaf_pkg_list.write("{};{};{};{};{}\n".format(pkg_name, pkg_vers, pkg_desc, dependencies, url))
    leaf_pkg_list.close()

    print("[*] Uploading leaf.pkglist")
    sftp_con.put("leaf.pkglist")
    os.remove("leaf.pkglist")

    sftp_con.close()
    print("[*] Done!")
    

if(__name__ == "__main__"):
    try:
        main()
    except KeyboardInterrupt:
        print("[*] Keyboard interrupt received.")
        exit(0)
