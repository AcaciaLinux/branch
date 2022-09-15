import os
import shutil
import time

from log import blog
from pyleaf import pyleafcore
from pathlib import Path


LAUNCH_DIR = os.getcwd()

# checks if the build environment is setup
def check_buildenv():
    # 3 directories required for overlayFS
    root_dir = os.path.join(LAUNCH_DIR, "realroot")
    cross_dir = os.path.join(LAUNCH_DIR, "crosstools")
    diff_dir = os.path.join(LAUNCH_DIR, "diffdir")
    work_dir = os.path.join(LAUNCH_DIR, "overlay")
    temp_dir = os.path.join(LAUNCH_DIR, "temproot")

    # check if paths exist..
    if(not os.path.exists(root_dir)):
        os.mkdir(root_dir)

    if(not os.path.exists(cross_dir)):
        os.mkdir(cross_dir)

    if(not os.path.exists(diff_dir)):
        os.mkdir(diff_dir)

    if(not os.path.exists(work_dir)):
        os.mkdir(work_dir)

    if(not os.path.exists(temp_dir)):
        os.mkdir(temp_dir)

    # control file exists if installed
    control_file = os.path.join(root_dir, "installed")

    if(not os.path.exists(control_file)):
        deploy_buildenv(root_dir, diff_dir, work_dir, temp_dir)

    control_file = os.path.join(cross_dir, "installed")

    if(not os.path.exists(control_file)):
        deploy_crossenv(cross_dir, diff_dir, work_dir, temp_dir)


    blog.info("Build environment setup completed.")

# installs packages to overlayfs temproot
def install_pkgs(packages):
    temp_dir = os.path.join(LAUNCH_DIR, "temproot")
    
    leafcore = pyleafcore.Leafcore()
    leafcore.setBoolConfig(pyleafcore.LeafConfig_bool.CONFIG_NOASK, True)
    leafcore.setRootDir(temp_dir)
    leafcore.a_update()

    if(not packages is None):
        leafcore.a_install(packages)

def deploy_buildenv(root_dir, diff_dir, work_dir, temp_dir):
    leafcore = pyleafcore.Leafcore()
    leafcore.setBoolConfig(pyleafcore.LeafConfig_bool.CONFIG_NOASK, True)
    leafcore.setRootDir(root_dir)
    leafcore.a_update()
    
    pkgs = ["base", "base-packages", "util-linux", "gcc"]

    leafcore.a_install(pkgs)
    Path(os.path.join(root_dir, "installed")).touch()

    blog.info("Realroot deployment completed.")

def deploy_crossenv(cross_dir, diff_dir, work_dir, temp_dir):
    leafcore = pyleafcore.Leafcore()
    leafcore.setBoolConfig(pyleafcore.LeafConfig_bool.CONFIG_NOASK, True)
    leafcore.setRootDir(cross_dir)
    leafcore.a_update()
    
    pkgs = ["crosstools"]

    leafcore.a_install(pkgs)
    Path(os.path.join(cross_dir, "installed")).touch()

    blog.info("Crossroot deployment completed.")


# first mount the overlayfs
def setup_env(use_crossroot):
    # 3 directories required for overlayFS
    root_dir = os.path.join(LAUNCH_DIR, "realroot")
    cross_dir = os.path.join(LAUNCH_DIR, "crosstools")
    diff_dir = os.path.join(LAUNCH_DIR, "diffdir")
    work_dir = os.path.join(LAUNCH_DIR, "overlay")
    temp_dir = os.path.join(LAUNCH_DIR, "temproot")

    if(not Path(temp_dir).is_mount()):
        blog.info("Mounting overlayfs..")
     
        if(use_crossroot):
            blog.info("Build requested using crosstools..")
            os.system("mount -t overlay overlay -o lowerdir={},upperdir={},workdir={} {}".format(cross_dir, diff_dir, work_dir, temp_dir))
        else:
            os.system("mount -t overlay overlay -o lowerdir={},upperdir={},workdir={} {}".format(root_dir, diff_dir, work_dir, temp_dir))
    else:
        # unclean shutdown, cleanup and remount
        clean_env()
        remount_env(use_crossroot)

    # bind devfs
    blog.info("Binding devfs...")
    dev_fs = os.path.join(temp_dir, "dev")
    os.system("mount --bind /dev {}".format(dev_fs))


# remount overlayfs
def remount_env(use_crossroot):
    root_dir = os.path.join(LAUNCH_DIR, "realroot")
    cross_dir = os.path.join(LAUNCH_DIR, "crosstools")
    diff_dir = os.path.join(LAUNCH_DIR, "diffdir")
    overlay_dir = os.path.join(LAUNCH_DIR, "overlay")
    temp_dir = os.path.join(LAUNCH_DIR, "temproot")
    
    blog.info("Remounting overlayfs..")
    if(use_crossroot):
        os.system("mount -t overlay overlay -o lowerdir={},upperdir={},workdir={} {}".format(cross_dir, diff_dir, overlay_dir, temp_dir))
    else:
        os.system("mount -t overlay overlay -o lowerdir={},upperdir={},workdir={} {}".format(root_dir, diff_dir, overlay_dir, temp_dir))
  
    blog.info("Syncing filesystem..")
    os.system("sync")

    blog.info("Remounting devfs..")
    dev_fs = os.path.join(temp_dir, "dev")
    os.system("mount --bind /dev {}".format(dev_fs))

def clean_env():
    diff_dir = os.path.join(LAUNCH_DIR, "diffdir")
    work_dir = os.path.join(LAUNCH_DIR, "overlay")
    temp_dir = os.path.join(LAUNCH_DIR, "temproot")
    dev_fs = os.path.join(temp_dir, "dev")

    blog.info("Unmounting devfs..")
    
    devfs_umount_failed = False
    
    while(os.path.ismount(dev_fs)):
        if(devfs_umount_failed):
            blog.warn("Unmounting devfs failed. Retrying...")
            os.system("umount {}".format(dev_fs))
            os.system("sync")
            time.sleep(1)
        else:
            os.system("umount {}".format(dev_fs))
            devfs_umount_failed = True

    blog.info("Unmounted devfs.")
    blog.info("Syncing filesystem..")
    os.system("sync")

    blog.info("Unmounting overlayfs..")
    while(os.path.ismount(temp_dir)):
        
        if(devfs_umount_failed):
            blog.warn("Unmounting overlayfs failed. Retrying...")
            os.system("umount {}".format(temp_dir))
            os.system("sync")
            time.sleep(1)
        else:
            os.system("umount {}".format(temp_dir))

    blog.info("Unmounted overlayfs.")

    blog.info("Syncing filesystem..")
    os.system("sync")

    # recreate dirs
    shutil.rmtree(diff_dir)
    shutil.rmtree(work_dir)
        
    target_busy = True
    while target_busy:
        try:
            shutil.rmtree(temp_dir)
            target_busy = False
        except OSError:
            blog.warn("Temp dir is busy..")
            time.sleep(2)

    os.mkdir(diff_dir)
    os.mkdir(work_dir)
    os.mkdir(temp_dir)

def get_build_path():
    return os.path.join(LAUNCH_DIR, "temproot")
