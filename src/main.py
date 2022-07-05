# Branch - The AcaciaLinux package build system
# Copyright (c) 2021-2022 zimsneexh (https://zsxh.eu/)

# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

import sys
import os
import argparse
import shutil
from leafpkg import initpkg
from leafpkg import tarpkg
from leafpkg import pushpkg
from leafpkg import lfpkg
from config import config
from pkgbuild import build
from pkgbuild import bpbutil
from log import blog

def main():
    print("Branch - The AcaciaLinux packaging utility.")

    conf = config.load_config()
    if(conf == -1):
        blog.error("Unable to continue. Exit Code: -1")
        return -1

    argparser = argparse.ArgumentParser(description="The AcaciaLinux packaging utility.")
    argparser.add_argument("-b", "--build", help="Builds a package.bpb file and installs to a new leaf package", action="store_true")
    argparser.add_argument("-pk", "--pack", help="Packs a leaf.pkg file to a lfpkg file", action="store_true")
    argparser.add_argument("-pu", "--push", help="Pushes a leaf.pkg file to a remote server", action="store_true")
    argparser.add_argument("-r", "--reconf", help="Reruns the branch configuration assistant", action="store_true")
    argparser.add_argument("-i", "--init", help="Initializes a new leaf.pkg file in cwd", action="store_true")
    argparser.add_argument("-bpb", "--bpbutil", help="Runs the branch package build utility.", action="store_true")
    argparser.add_argument("-sc", "--skipchecks", help="Skip all checks that require interaction.", action="store_true")

    args = argparser.parse_args()
    
    # Count number of active variables.
    lenvar = 0
    for key in vars(args):
        if(args.__dict__[key]):
            lenvar = lenvar + 1

    res = argCheck(args, conf, lenvar)
    blog.info("Operation completed. Exit code: {}".format(res))
    return res

def argCheck(args, conf, lenvar):
    if(args.init): 
        if(lenvar > 1):
            blog.warn("'init' is a standalone argument. Ignoring other arguments.")

        leafpkg = initpkg.pkg_utility()
        pkgpath = initpkg.newpkg(leafpkg)

        if(pkgpath == 0):
            blog.error("Package path already exists.")
            if(args.skipchecks):
                blog.warn("Skipping checks as you requested. Deleting package directory.")
                shutil.rmtree(leafpkg.getPkgPath())
                initpkg.newpkg(leafpkg)
            else:
                print("Do you want to delete the existing package directory? (y/n)")
                if(input() == 'y'):
                    blog.info("Deleting package directory..")
                    shutil.rmtree(leafpkg.getPkgDirectory())
                    initpkg.newpkg(leafpkg)
                else:
                    blog.error("Cannot continue.")
                    return -1

        blog.info("Package directory created for \"{}\": {}".format(leafpkg.name, leafpkg.pkg_root))
        return 0

    elif(args.reconf):
        if(lenvar > 1):
            blog.warn("'reconf' is a standalone argument. Ignoring other arguments.")

        return config.reconf()
    elif(args.bpbutil):
        if(lenvar > 1):
            blog.warn("'bpbutil' is a standalone argument. Ignoring other arguments.")

        return bpbutil.createbpb()
    else:
        if(args.build):
            blog.info("Running build step..")
            res = build.build(args.skipchecks)
            if(res == -1):
                blog.error("Build failed!")
                return -1
        
        if(args.pack):
            blog.info("Running pack step..")
            res = tarpkg.pack(args.skipchecks)
            if(res == -1):
                blog.error("Packaging failed!")
                return -1

        if(args.push):
            blog.info("Running push step..")
            res = pushpkg.push(conf, args.skipchecks)
            if(res == -1):
                blog.error("Pushing failed.")
                return -1

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        blog.warn("Exiting on Keyboard interrupt.")
        exit(0)
