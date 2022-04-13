# Main file
# Author: zimsneexh
# Copyright (c) zimsneexh (The AcaciaLinux project), 2022

import sys
from utils import help
from leafpkg import initpkg
from leafpkg import tarpkg
from leafpkg import pushpkg
from leafpkg import lfpkg
from config import config

def main():
    conf = config.load_config()
    args = len(sys.argv)

    if(args == 2):
        if(sys.argv[1] == "init"):
            initpkg.newpkg() 

        elif(sys.argv[1] == "pack"):
            tarpkg.pack()

        elif(sys.argv[1] == "push"):
            pushpkg.push(conf)

        elif(sys.argv[1] == "packpush"):
            tarpkg.pack()
            pushpkg.push(conf)
        
        elif(sys.argv[1] == "reconf"):
            config.reconf()

        else:
           help.helpMsg() 
    else:
        help.helpMsg()
        exit(0)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        print("Exiting on Keyboard interrupt.")
        exit(0)
