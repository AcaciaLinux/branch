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
        if(deploy_buildenv(root_dir, diff_dir, work_dir, temp_dir) != 0):
            blog.error("Real root deployment failed.")
            exit(-1)

    control_file = os.path.join(cross_dir, "installed")

    if(not os.path.exists(control_file)):
        if(deploy_crossenv(cross_dir, diff_dir, work_dir, temp_dir) != 0):
            blog.error("Crosstools deployment failed.")
            exit(-1)

    blog.info("Build environment setup completed.")

# installs packages to overlayfs temproot
def install_pkgs(packages):
    temp_dir = os.path.join(LAUNCH_DIR, "temproot")
    
    leafcore = None
    try:
        leafcore = pyleafcore.Leafcore()
    except Exception:
        blog.error("cleaf not found. Exiting.")
        exit(-1)

    leafcore.setBoolConfig(pyleafcore.LeafConfig_bool.CONFIG_NOASK, True)
    leafcore.setBoolConfig(pyleafcore.LeafConfig_bool.CONFIG_FORCEOVERWRITE, True)
    leafcore.setRootDir(temp_dir)

    leaf_error = leafcore.a_update()
    if(leaf_error != 0):
        blog.error("Leaf error code: {}".format(leaf_error))
        return -1

    if(packages):
        leaf_error = leafcore.a_install(packages)
        if(leaf_error != 0):
            blog.error("Leaf error code: {}".format(leaf_error))
            return -1

    blog.info("Package install completed.")
    return 0

def deploy_buildenv(root_dir, diff_dir, work_dir, temp_dir):
    leafcore = None
    try:
        leafcore = pyleafcore.Leafcore()
    except Exception:
        blog.error("cleaf not found. Exiting.")
        exit(-1)

    leafcore.setBoolConfig(pyleafcore.LeafConfig_bool.CONFIG_NOASK, True)
    leafcore.setRootDir(root_dir)

    leaf_error = leafcore.a_update()
    if(leaf_error != 0):
        blog.error("Leaf error code: {}".format(leaf_error))
        return -1

    pkgs = ["base", "base-packages", "util-linux", "gcc"]

    leaf_error = leafcore.a_install(pkgs)
    if(leaf_error != 0):
        blog.error("Leaf error code: {}".format(leaf_error))
        return -1

    Path(os.path.join(root_dir, "installed")).touch()
    blog.info("Realroot deployment completed.")
    return 0

def deploy_crossenv(cross_dir, diff_dir, work_dir, temp_dir):
    leafcore = None
    try:
        leafcore = pyleafcore.Leafcore()
    except Exception:
        blog.error("cleaf not found. Exiting.")
        exit(-1)

    leafcore.setBoolConfig(pyleafcore.LeafConfig_bool.CONFIG_NOASK, True)
    leafcore.setRootDir(cross_dir)

    leaf_error = leafcore.a_update()
    if(leaf_error != 0):
        blog.error("Leaf error code: {}".format(leaf_error))
        return -1

    pkgs = ["crosstools"]

    leaf_error = leafcore.a_install(pkgs)
    if(leaf_error != 0):
        blog.error("Leaf error code: {}".format(leaf_error))
        return -1

    Path(os.path.join(cross_dir, "installed")).touch()
    blog.info("Crossroot deployment completed.")
    return 0

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
    
    setup_kfs()

def setup_kfs():
    blog.info("Mounting virtual kernel file systems..")
    
    # bind devfs
    blog.info("Binding devfs...")
    dev_fs = os.path.join(temp_dir, "dev")
    os.system("mount -v --bind /dev {}".format(dev_fs))

    blog.info("Binding pts..") 
    dev_pts = os.path.join(dev_fs, "pts")
    os.system("mount -v --bind /dev/pts {}".format(dev_pts))

    blog.info("Mounting proc..")
    proc_fs = os.path.join(temp_dir, "proc")
    os.system("mount -vt proc proc {}".format(proc_fs))

    blog.info("Mounting sysfs..")
    sys_fs = os.path.join(temp_dir, "sys")
    os.system("mount -vt sysfs sysfs {}".format(sys_fs))

    blog.info("Mounting tmpfs..")
    tmp_fs = os.path.join(temp_dir, "run")
    os.system("mount -vt tmpfs tmpfs {}".format(tmp_fs))


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
    
    setup_kfs()

def clean_env():
    diff_dir = os.path.join(LAUNCH_DIR, "diffdir")
    work_dir = os.path.join(LAUNCH_DIR, "overlay")
    temp_dir = os.path.join(LAUNCH_DIR, "temproot")
    
    dev_fs = os.path.join(temp_dir, "dev")
    dev_pts = os.path.join(dev_fs, "pts")

    sys_fs = os.path.join(temp_dir, "sys")
    proc_fs = os.path.join(temp_dir, "proc")
    run_fs = os.path.join(temp_dir, "run")

    umount_busy_wait(dev_fs)
    umount_busy_wait(dev_pts)
    umount_busy_wait(sys_fs)
    umount_busy_wait(proc_fs)
    umount_busy_wait(run_fs)

    blog.info("Syncing filesystem..")
    os.system("sync")

    umount_busy_wait(temp_dir)

    blog.info("Syncing filesystem..")
    os.system("sync")

    # recreate dirs
    shutil.rmtree(diff_dir)
    shutil.rmtree(work_dir)
    shutil.rmtree(temp_dir)

    os.mkdir(diff_dir)
    os.mkdir(work_dir)
    os.mkdir(temp_dir)

def umount_busy_wait(path):
    blog.info("Unmounting {}".format(path))
    umount_failed = False
    
    while(os.path.ismount(path)):
        if(umount_failed):
            blog.warn("Unmounting failed. Retrying...")
            os.system("umount {}".format(path))
            os.system("sync")
            time.sleep(2)
        else:
            os.system("umount {}".format(path))
            umount_failed = True
    
    blog.info("Unmounted.")

def get_build_path():
    return os.path.join(LAUNCH_DIR, "temproot")
