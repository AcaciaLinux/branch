# Main file
# Author: zimsneexh
# Copyright (c) zimsneexh (The AcaciaLinux project), 2022

import sys
import help
import initpkg
import tarpkg
import pushpkg
import config

def main():
    config.load_config()

    args = len(sys.argv)

    if(args == 2):
        if(sys.argv[1] == "init"):
            initpkg.newpkg() 

        elif(sys.argv[1] == "pack"):
            tarpkg.pack()

        elif(sys.argv[1] == "push"):
            pushpkg.push()

        elif(sys.argv[1] == "packpush"):
            print()

        else:
           help.helpMsg() 
    else:
        help.helpMsg()
        exit(0)

if __name__ == "__main__":
    main()
