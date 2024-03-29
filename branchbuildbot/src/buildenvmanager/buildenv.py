"""
Buildenvironment manager module
"""
import os
import shutil
import time
import platform
from pathlib import Path
from datetime import datetime

import psutil
import blog
from pyleafcore import LeafConfig_bool, LeafConfig_string, Leafcore, LeafException
from buildenvmanager import buildenv

LAUNCH_DIR = os.getcwd()
leafcore_instance = None

def cpu_test() -> float:
    """
    Runs a very simple CPU performance test

    :return: (float) performance metric (lower is better)
    """
    blog.info("Running CPU performance test..")
    cpu_count = psutil.cpu_count(logical=True)
    start_time = datetime.now().timestamp()
    
    value = 0
    for i in range(100000000):
        value = value * i

    end_time = datetime.now().timestamp()
    res = (end_time - start_time) / cpu_count
    blog.info("CPU performance results (lower is better): {}".format(res))
    return round(res, 6) 

def get_host_info() -> dict:
    """
    Get host info array to submit to masterserver

    :return: (dict) Dictionary of Hostinfo
    """
    info = { }

    with open("/proc/cpuinfo", "r") as f:
        file_info = f.readlines()

    cpuinfo = [x.strip().split(":")[1] for x in file_info if "model name" in x]
    info["Architecture"] = platform.machine()
    info["Hostname"] = platform.node()
    info["Host Python Version"] = platform.python_version()
    info["Host Kernel"] = platform.system() + " " + platform.release()
    info["Host Distribution"] = platform.freedesktop_os_release()["NAME"]
    info["Host libc"] = platform.libc_ver()[0] + " " + platform.libc_ver()[1]
    info["CPU count"] = psutil.cpu_count(logical=True)
    if (len(cpuinfo) > 0):
        info["CPU name"] = cpuinfo[0]
    else:
        info["CPU name"] = "unknown"
    info["Memory available"] = "{}GB".format(round(psutil.virtual_memory().total / (1024*1024*1024), 2))
    info["Performance Rating"] = cpu_test() 
    return info

def init_leafcore(pkglist_url: str) -> bool:
    """
    Initialize leafcore global
    """
    global leafcore_instance

    blog.debug("Initializing leafcore..")
    try:
        leafcore_instance = Leafcore()
    except Exception as ex:
        blog.error("Failed to initialize leafcore. Exception raised: {}".format(ex))
        return False

    leafcore_instance.setBoolConfig(LeafConfig_bool.CONFIG_NOASK, True)
    leafcore_instance.setBoolConfig(LeafConfig_bool.CONFIG_FORCEOVERWRITE, True)
    leafcore_instance.setBoolConfig(LeafConfig_bool.CONFIG_NOPROGRESS, True)
    leafcore_instance.setStringConfig(LeafConfig_string.CONFIG_PKGLISTURL, pkglist_url)
    leafcore_instance.setStringConfig(LeafConfig_string.CONFIG_DOWNLOADCACHE, os.path.join(LAUNCH_DIR, "leafcache/"))
    blog.debug("Leafcore initialized.")
    return True

def fetch_leaf_logs():
    """
    Fetch latest leafcore log
    """
    global leafcore_instance
    return leafcore_instance.get_log()

def clear_leaf_logs():
    """
    Clear leafcore log if leafcore_instance is not None
    """
    global leafcore_instance
    
    # check if leafcore instance is None before clearing
    if(leafcore_instance is None):
        return

    return leafcore_instance.clear_log()

def drop_buildenv():
    """
    Drop the current environment
    """
    root_dir = os.path.join(LAUNCH_DIR, "realroot")
    cross_dir = os.path.join(LAUNCH_DIR, "crosstools")
    
    try:
        shutil.rmtree(root_dir)
    except FileNotFoundError:
        blog.info("No real root available.")

    try:
        shutil.rmtree(cross_dir)
    except FileNotFoundError:
        blog.info("No cross root available.")

def check_buildenv(crossroot_enabled: bool, realroot_enabled: bool, realroot_pkgs: list) -> bool:
    """
    Check the current build environment
    """
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

    # check if diffdir is empty
    if(len(os.listdir(diff_dir)) != 0):
        blog.warn("Unclean shutdown. Removing diffdir..")
        shutil.rmtree(diff_dir)
        os.mkdir(diff_dir)

    # check if workdir is empty
    if(len(os.listdir(work_dir)) != 0):
        blog.warn("Unclean shutdown. Removing workdir..")
        shutil.rmtree(work_dir)
        os.mkdir(work_dir)

    # check if workdir is empty
    if(len(os.listdir(temp_dir)) != 0):
        blog.warn("Unclean shutdown. Removing tempdir..")
        shutil.rmtree(temp_dir)
        os.mkdir(temp_dir)


    # control file exists if installed
    control_file = os.path.join(root_dir, "installed")
    
    if(realroot_enabled):
        if(not os.path.exists(control_file)):
            if(deploy_buildenv(root_dir, realroot_pkgs) != 0):
                blog.error("Real root deployment failed.")
                return False
    else:
        blog.warn("Deployment config: Will not deploy realroot.")


    control_file = os.path.join(cross_dir, "installed")
    
    if(crossroot_enabled):
        if(not os.path.exists(control_file)):
            if(not deploy_crossenv(cross_dir)):
                blog.error("Crosstools deployment failed.")
                return False
    else:
        blog.warn("Deployment config: Will not deploy crossroot.")


    blog.info("Build environment setup completed.")
    return True

def check_host_binary(binary) -> bool:
    """
    Check if a host binary is accessible through the PATH environment var
    """
    for path in os.environ["PATH"].split(":"):
        for root, dirs, files in os.walk(path):
            for file in files:
                if file == binary:
                    return True

    return False

def install_pkgs(packages) -> bool:
    """
    Install packages in the overlayfs temproot
    """
    global leafcore_instance

    temp_dir = os.path.join(LAUNCH_DIR, "temproot")

    # set root dir properly
    leafcore_instance.setStringConfig(LeafConfig_string.CONFIG_ROOTDIR, temp_dir)

    try:
        leafcore_instance.a_update()
    except LeafException as ex:
        blog.error("Leaf error when executing a_update() ({}): {}".format(ex.code, ex.message))
        return False

    if(packages):
        try:
            leafcore_instance.a_install(packages)
        except LeafException as ex:
            blog.error("Leaf error when executing a_install({}) ({}): {}".format(packages, ex.code, ex.message))
            return False

    blog.info("Package install completed.")
    return True

def deploy_buildenv(root_dir, realroot_pkgs) -> bool:
    """
    Deploy the realroot build environment
    """
    global leafcore_instance

    leafcore_instance.setStringConfig(LeafConfig_string.CONFIG_ROOTDIR, root_dir)

    try:
        leafcore_instance.a_update()
    except LeafException as ex:
        blog.error("Leaf error when executing a_update() ({}): {}".format(ex.code, ex.message))
        return False

    try:
        leafcore_instance.a_install(realroot_pkgs)
    except LeafException as ex:
        blog.error("Leaf error when executing a_install({}) ({}): {}".format(realroot_pkgs, ex.code, ex.message))
        return False

    Path(os.path.join(root_dir, "installed")).touch()
    blog.info("Realroot deployment completed.")
    
    resolv_conf = os.path.join(root_dir, "etc/resolv.conf")

    if(os.path.exists(resolv_conf)):
        os.remove(resolv_conf)
    
    with open(resolv_conf, "w") as f:
        f.write("nameserver 1.1.1.1\n")
    
    blog.info("Resolver set.")
    return True

def deploy_crossenv(cross_dir) -> bool:
    global leafcore_instance

    leafcore_instance.setStringConfig(LeafConfig_string.CONFIG_ROOTDIR, cross_dir)

    try:
        leafcore_instance.a_update()
    except LeafException as ex:
        blog.error("Leaf error when executing a_update() ({}): {}".format(ex.code, ex.message))
        return False

    pkgs = ["crosstools"]

    try:
        leafcore_instance.a_install(pkgs)
    except LeafException as ex:
        blog.error("Leaf error when executing a_install({}) ({}): {}".format(pkgs, ex.code, ex.message))
        return False

    Path(os.path.join(cross_dir, "installed")).touch()
    blog.info("Crossroot deployment completed.")

    resolv_conf = os.path.join(cross_dir, "etc/resolv.conf")

    if(os.path.exists(resolv_conf)):
        os.remove(resolv_conf)
    
    with open(resolv_conf, "w") as f:
        f.write("nameserver 1.1.1.1\n")
    
    blog.info("Resolver set.")
    return True

def setup_env(use_crossroot: bool) -> bool:
    """
    Setup the buildbot environment

    :param use_crossroot: Use crossroot to handle this buildrequest
    :return: (bool) True -> OK, False -> Couldn't setup
    """

    # actual filesystems
    root_dir = os.path.join(LAUNCH_DIR, "realroot")
    cross_dir = os.path.join(LAUNCH_DIR, "crosstools")
    
    # 3 directories required for overlayFS
    diff_dir = os.path.join(LAUNCH_DIR, "diffdir")
    work_dir = os.path.join(LAUNCH_DIR, "overlay")
    temp_dir = os.path.join(LAUNCH_DIR, "temproot")

    blog.info("Upgrading real root..")
    if(not upgrade_real_root()):
        return False

    blog.info("Upgrading cross root..")
    if(not upgrade_cross_root()):
        return False

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
    return True

def setup_kfs():
    temp_dir = os.path.join(LAUNCH_DIR, "temproot")
    blog.info("Mounting virtual kernel file systems..")
    
    # bind devfs
    blog.info("Binding devfs...")
    dev_fs = os.path.join(temp_dir, "dev")
    os.system("mount -v --bind /dev {}".format(dev_fs))

    blog.info("Mounting pts..") 
    dev_pts = os.path.join(dev_fs, "pts")
    os.system("mount -v -t devpts devpts {}".format(dev_pts))

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
    blog.info("Cleaning up build environment..")
    diff_dir = os.path.join(LAUNCH_DIR, "diffdir")
    work_dir = os.path.join(LAUNCH_DIR, "overlay")
    temp_dir = os.path.join(LAUNCH_DIR, "temproot")
    
    dev_fs = os.path.join(temp_dir, "dev")
    dev_pts = os.path.join(dev_fs, "pts")

    sys_fs = os.path.join(temp_dir, "sys")
    proc_fs = os.path.join(temp_dir, "proc")
    run_fs = os.path.join(temp_dir, "run")

    umount_busy_wait(dev_pts)
    umount_busy_wait(dev_fs)
    
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
    
    blog.info("Clearing leafcore logs..")
    buildenv.clear_leaf_logs()
    blog.info("Cleanup completed.")


def upgrade_cross_root() -> bool:
    root_dir = os.path.join(LAUNCH_DIR, "crosstools")
    global leafcore_instance

    leafcore_instance.setStringConfig(LeafConfig_string.CONFIG_ROOTDIR, root_dir)

    try:
        leafcore_instance.a_update()
    except LeafException as ex:
        blog.error(f"Leaf error when executing a_update() ({ex.code}): {ex.message}")
        blog.error("Failed to update cross root. Cannot continue.")
        return False

    try:
        leafcore_instance.a_upgrade([])
    except LeafException as ex:
        blog.error(f"Leaf error when executing a_upgrade([]) ({ex.code}): {ex.message}")
        blog.error("Failed to upgrade cross root. Cannot continue")
        return False
    
    leafcore_instance.clear_log()
    return True

def upgrade_real_root() -> bool:
    root_dir = os.path.join(LAUNCH_DIR, "realroot")
    global leafcore_instance

    leafcore_instance.setStringConfig(LeafConfig_string.CONFIG_ROOTDIR, root_dir)

    try:
        leafcore_instance.a_update()
    except LeafException as ex:
        blog.error(f"Leaf error when executing a_update() ({ex.code}): {ex.message}")
        blog.error("Failed to update real root. Cannot continue.")
        return False

    try:
        leafcore_instance.a_upgrade([])
    except LeafException as ex:
        blog.error(f"Leaf error when executing a_upgrade([]) ({ex.code}): {ex.message}")
        blog.error("Failed to upgrade real root. Cannot continue")
        return False

    leafcore_instance.clear_log()
    return True

def umount_busy_wait(path: str):
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
    """
    Get path to temproot
    """
    return os.path.join(LAUNCH_DIR, "temproot")
