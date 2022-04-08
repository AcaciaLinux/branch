import os
import tarpkg
import lfpkg

def push():
    if not("leaf.pkg" in os.listdir(os.getcwd())):
        print("This does not appear to be a package directory. Aborting.")
        exit(-1)

    leafpkg = lfpkg.parse()

    pwd = os.path.abspath(os.path.join(os.getcwd(), os.pardir))
    tar_name = "{}-{}.lfpkg".format(leafpkg.name, leafpkg.version)
    
    if not(tar_name in os.listdir(pwd)):
        print("{} does not have a package file.".format(pwd))
        print("Do you want to run pack? (y/n)")

        answ = input()
        if(answ.lower() == "y"):
            tarpkg.pack()
        else:
            exit(-1)

    #sftp
    print("todo: push sftp")
       
        

        


