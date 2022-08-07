from log import blog

from pyleaf import pyleafcore
from pathlib import Path
import os
import shutil

LAUNCH_DIR = os.getcwd()

# checks if the build environment is setup
def check_buildenv():
    # 3 directories required for overlayFS
    root_dir = os.path.join(LAUNCH_DIR, "realroot")
    diff_dir = os.path.join(LAUNCH_DIR, "diffdir")
    work_dir = os.path.join(LAUNCH_DIR, "overlay")
    temp_dir = os.path.join(LAUNCH_DIR, "temproot")

    # check if paths exist..
    if(not os.path.exists(root_dir)):
        os.mkdir(root_dir)

    if(not os.path.exists(diff_dir)):
        os.mkdir(diff_dir)

    if(not os.path.exists(work_dir)):
        os.mkdir(work_dir)

    if(not os.path.exists(temp_dir)):
        os.mkdir(temp_dir)

    # control file exists if installed
    control_file = os.path.join(root_dir, "installed")

    if(os.path.exists(control_file)):
        setup_env(root_dir, diff_dir, work_dir, temp_dir)
    else:
        deploy_buildenv(root_dir, diff_dir, work_dir, temp_dir)

# installs packages to overlayfs temproot
def install_pkgs(packages):
    temp_dir = os.path.join(LAUNCH_DIR, "temproot")
    
    leafcore = pyleafcore.Leafcore()
    leafcore.setVerbosity(1)
    leafcore.setRootDir(temp_dir)
    leafcore.a_update()

    if(not packages is None):
        leafcore.a_install(packages)

def deploy_buildenv(root_dir, diff_dir, work_dir, temp_dir):

    # pyleaf stub
    leafcore = pyleafcore.Leafcore()
    leafcore.setVerbosity(1)
    leafcore.setRootDir(root_dir)
    leafcore.a_update()
    
    pkgs = ["base", "base-packages", "util-linux", "gcc"]

    leafcore.a_install(pkgs)
    Path(os.path.join(root_dir, "installed")).touch()

    blog.info("Deployment completed.")
    setup_env(root_dir, diff_dir, work_dir, temp_dir)

# first mount the overlayfs
def setup_env(root_dir, diff_dir, overlay_dir, temp_dir):
    if(not Path(temp_dir).is_mount()):
        blog.info("Mounting overlayfs..")
        os.system("mount -t overlay overlay -o lowerdir={},upperdir={},workdir={} {}".format(root_dir, diff_dir, overlay_dir, temp_dir))
    else:
        # unclean shutdown, cleanup and remount
        clean_env()
        remount_env()


# remount overlayfs
def remount_env():
    root_dir = os.path.join(LAUNCH_DIR, "realroot")
    diff_dir = os.path.join(LAUNCH_DIR, "diffdir")
    overlay_dir = os.path.join(LAUNCH_DIR, "overlay")
    temp_dir = os.path.join(LAUNCH_DIR, "temproot")

    os.system("mount -t overlay overlay -o lowerdir={},upperdir={},workdir={} {}".format(root_dir, diff_dir, overlay_dir, temp_dir))

def clean_env():
    root_dir = os.path.join(LAUNCH_DIR, "realroot")
    diff_dir = os.path.join(LAUNCH_DIR, "diffdir")
    work_dir = os.path.join(LAUNCH_DIR, "overlay")
    temp_dir = os.path.join(LAUNCH_DIR, "temproot")
    
    os.system("umount {}".format(temp_dir))
    
    # recreate dirs
    shutil.rmtree(diff_dir)
    shutil.rmtree(work_dir)
    shutil.rmtree(temp_dir)
    os.mkdir(diff_dir)
    os.mkdir(work_dir)
    os.mkdir(temp_dir)

def get_build_path():
    return os.path.join(LAUNCH_DIR, "temproot")
