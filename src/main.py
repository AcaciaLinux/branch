# Main file
# Author: zimsneexh
# Copyright (c) zimsneexh (The AcaciaLinux project), 2022

import sys
import argparse
from leafpkg import initpkg
from leafpkg import tarpkg
from leafpkg import pushpkg
from leafpkg import lfpkg
from config import config
from pkgbuild import build
from pkgbuild import bpbutil

def main():
    conf = config.load_config()
    
    argparser = argparse.ArgumentParser(description="The AcaciaLinux packaging utility.")
    

    argparser.add_argument("-b", "--build", help="Builds a package.bpb file and installs to a new leaf package", action="store_true")
    argparser.add_argument("-pk", "--pack", help="Packs a leaf.pkg file to a lfpkg file", action="store_true")
    argparser.add_argument("-pu", "--push", help="Pushes a leaf.pkg file to a remote server", action="store_true")
    argparser.add_argument("-r", "--reconf", help="Reruns the branch configuration assistant", action="store_true")
    argparser.add_argument("-i", "--init", help="Initializes a new leaf.pkg file in cwd", action="store_true")
    argparser.add_argument("-bpb", "--bpbutil", help="Runs the branch package build utility.", action="store_true")
    argparser.add_argument("-c", "--clean", help="Cleans the current directory.", action="store_true")
    args = argparser.parse_args()
    

    lenvar = 0

    for key in vars(args):
        if(args.__dict__[key]):
            lenvar = lenvar + 1

    argCheck(args, conf, lenvar)


def argCheck(args, conf, lenvar):
    if(args.init):
        if(lenvar > 1):
            print("'init' is a standalone argument. Only running init.")

        initpkg.pkg_utility() 
    elif(args.reconf):
        if(lenvar > 1):
            print("'reconf' is a standalone argument. Only running reconf.")

        config.reconf()
    elif(args.bpbutil):
        if(lenvar > 1):
            print("'bpbutil' is a standalone argument. Only running bpbutil.")

        bpbutil.createbpb()
    else:
        if(args.build):
            print("Running build step..")
            build.build()
        if(args.pack):
            print("Running pack step..")
            tarpkg.pack()
        if(args.push):
            print("Running push step..")
            pushpkg.push(conf)
        if(args.clean):
            print("Running clean step..")
            build.cleanAll()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        print("Exiting on Keyboard interrupt.")
        exit(0)
