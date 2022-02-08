import os
import zipfile

def main():
    print("Branch - The AcaciaLinux packager")
    print("[*] Enter a package name: ")
    pkg_name = input()

    print("[*] Enter a package version: ")
    pkg_vers = input()

    pkg_sub_dir = "{}-{}".format(pkg_name, pkg_vers)
    pkg_work_dir = ""

    print("[*] Do you wish to create the pkg work directory in cwd? (y/n)")
    answ = input()

    if(answ == "y"):
        pkg_work_dir = os.path.join(os.getcwd(), pkg_sub_dir)
    elif(answ == "n"):
        print("[*] Enter workdirectory.. e.g: /packages/")
        pkg_work_dir = input()
    else:
        print("[!] Invalid answer.")
        exit(0)

    print("[*] Creating your pkg work directory at {}..".format(pkg_work_dir))
    try:
        os.mkdir(pkg_work_dir)
    except FileExistsError:
        print("[*] Package directory exists. Choose a different package directory.")
        exit(-1)


    print("[*] Creating data directory")
    os.mkdir(os.path.join(pkg_work_dir, "data"))

    print("[!!] Your pkg work directory is: ", pkg_work_dir)
    print("[!!] Set Package DESTDIR to ", os.path.join(pkg_work_dir, "data"))
    print("[!!] Entering bash shell.")
    print("[!!] Exit shell once you are done installing files to pkg data directory")
    os.system("bash")

    print("[*] Creating package file..") 
    filelist = []

    for root, dirs, files in os.walk(os.path.join(pkg_work_dir, "data"), topdown=True):
        for file in files:
            filelist.append(os.path.join(root, file))
    
    leaf_pkg_file = open(os.path.join(pkg_work_dir, "leaf.pkg"), "w")
    leaf_pkg_file.write("name={}\n".format(pkg_name))    
    leaf_pkg_file.write("version={}\n".format(pkg_vers))
    leaf_pkg_file.write("files=")
    
    for file in filelist:
        leaf_pkg_file.write("[{}]".format(os.path.relpath(file, os.path.join(pkg_work_dir, "data"))))

    leaf_pkg_file.write("\n")

    print("[*] Enter dependencies as String. [a][b][c][d]")
    dependencies = input()
    leaf_pkg_file.write("dependencies={}".format(dependencies))
    
    leaf_pkg_file.close()
    print("[*] Done creating leaf.pkg file")

    print("[*] Creating zip file..")
    
    pkg_file_zip = zipfile.ZipFile("{}-{}.lfpkg".format(pkg_name, pkg_vers), "w", zipfile.ZIP_DEFLATED)

    for root, dirs, files in os.walk(pkg_work_dir):
        for file in files:
            print("[*] Adding to zip file: {} ".format(file))
            pkg_file_zip.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), os.path.join(pkg_work_dir, '..')))

    pkg_file_zip.close()
    print("[*] Done. Finished package file is now in cwd")
    
if(__name__ == "__main__"):
    main()
