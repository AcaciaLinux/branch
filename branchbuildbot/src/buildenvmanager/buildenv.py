import os
import shutil
import time
import blog
import pyleafcore

from pathlib import Path
from buildenvmanager import buildenv
from config import config

LAUNCH_DIR = os.getcwd()
leafcore_instance = None

# leafcore init
def init_leafcore():
    global leafcore_instance

    blog.debug("Initializing leafcore..")
    try:
        leafcore_instance = pyleafcore.Leafcore()
    except Exception as ex:
        blog.error("Failed to initialize leafcore. Exception raised: {}".format(ex))
        return -1

    leafcore_instance.setBoolConfig(LeafConfig_bool.CONFIG_NOASK, True)
    leafcore_instance.setBoolConfig(LeafConfig_bool.CONFIG_FORCEOVERWRITE, True)
    leafcore_instance.setBoolConfig(LeafConfig_bool.CONFIG_NOPROGRESS, True)
    leafcore_instance.setStringConfig(LeafConfig_string.CONFIG_PKGLISTURL, config.config.get_config_option("Leaf")["PackagelistUrl"])
    blog.debug("Leafcore initialized.")
    return 0

# fetches logs
def fetch_leaf_logs():
    global leafcore_instance
    return leafcore_instance.get_log()

# clears logs post action
def clear_leaf_logs():
    global leafcore_instance
    return leafcore_instance.clear_log()

def drop_buildenv():
    root_dir = os.path.join(LAUNCH_DIR, "realroot")
    cross_dir = os.path.join(LAUNCH_DIR, "crosstools")
    
    shutil.rmtree(root_dir)
    shutil.rmtree(cross_dir)

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
            blog.error("Real root deployment failed. Sending system event to masterserver..")
            return -1

    control_file = os.path.join(cross_dir, "installed")

    if(not os.path.exists(control_file)):
        if(deploy_crossenv(cross_dir, diff_dir, work_dir, temp_dir) != 0):
            blog.error("Crosstools deployment failed. Sending system event to masterserver..")
            return -1

    blog.info("Build environment setup completed.")
    return 0

# Checks if a binary on the host is accessible through the PATH variable
def check_host_binary(binary):
    for path in os.environ["PATH"].split(":"):
        for root, dirs, files in os.walk(path):
            for file in files:
                if file == binary:
                    return True

    return False

# installs packages to overlayfs temproot
def install_pkgs(packages):
    global leafcore_instance

    temp_dir = os.path.join(LAUNCH_DIR, "temproot")

    # set root dir properly
    leafcore_instance.setStringConfig(LeafConfig_string.CONFIG_ROOTDIR, temp_dir)

    leaf_error = leafcore_instance.a_update()
    if(leaf_error != 0):
        blog.error("Leaf error code: {}".format(leaf_error))
        return -1

    if(packages):
        leaf_error = leafcore_instance.a_install(packages)
        if(leaf_error != 0):
            blog.error("Leaf error code: {}".format(leaf_error))
            return -1

    blog.info("Package install completed.")
    return 0

def deploy_buildenv(root_dir, diff_dir, work_dir, temp_dir):
    global leafcore_instance

    leafcore_instance.setStringConfig(LeafConfig_string.CONFIG_ROOTDIR, root_dir)

    leaf_error = leafcore_instance.a_update()
    if(leaf_error != 0):
        blog.error("Leaf error code: {}".format(leaf_error))
        return -1

    pkgs = ["base", "glibc", "gcc", "make", "bash", "sed", "grep", "gawk", "coreutils", "binutils", "findutils", "automake", "autoconf", "file", "gzip", "libtool", "m4", "groff", "patch", "texinfo", "which"]

    leaf_error = leafcore_instance.a_install(pkgs)
    if(leaf_error != 0):
        blog.error("Leaf error code: {}".format(leaf_error))
        return -1

    Path(os.path.join(root_dir, "installed")).touch()
    blog.info("Realroot deployment completed.")
    
    resolv_conf = os.path.join(root_dir, "etc/resolv.conf")

    if(os.path.exists(resolv_conf)):
        os.remove(resolv_conf)
    
    with open(resolv_conf, "w") as f:
        f.write("nameserver 1.1.1.1\n")
    
    blog.info("Resolver set.")
    return 0

def deploy_crossenv(cross_dir, diff_dir, work_dir, temp_dir):
    global leafcore_instance

    leafcore_instance.setStringConfig(LeafConfig_string.CONFIG_ROOTDIR, cross_dir)

    leaf_error = leafcore_instance.a_update()
    if(leaf_error != 0):
        blog.error("Leaf error code: {}".format(leaf_error))
        return -1

    pkgs = ["crosstools"]

    leaf_error = leafcore_instance.a_install(pkgs)
    if(leaf_error != 0):
        blog.error("Leaf error code: {}".format(leaf_error))
        return -1

    Path(os.path.join(cross_dir, "installed")).touch()
    blog.info("Crossroot deployment completed.")

    resolv_conf = os.path.join(cross_dir, "etc/resolv.conf")

    if(os.path.exists(resolv_conf)):
        os.remove(resolv_conf)
    
    with open(resolv_conf, "w") as f:
        f.write("nameserver 1.1.1.1\n")
    
    blog.info("Resolver set.")
    return 0

# first mount the overlayfs
def setup_env(use_crossroot):
    # 3 directories required for overlayFS
    root_dir = os.path.join(LAUNCH_DIR, "realroot")
    cross_dir = os.path.join(LAUNCH_DIR, "crosstools")
    diff_dir = os.path.join(LAUNCH_DIR, "diffdir")
    work_dir = os.path.join(LAUNCH_DIR, "overlay")
    temp_dir = os.path.join(LAUNCH_DIR, "temproot")

    blog.info("Upgrading real root..")
    if(upgrade_real_root() == -1):
        return -1

    if(upgrade_cross_root() == -1):
        return -1

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
    blog.info("Cleanup completed. Ready for commands.")


def upgrade_cross_root():
    root_dir = os.path.join(LAUNCH_DIR, "crosstools")
    global leafcore_instance

    leafcore_instance.setStringConfig(LeafConfig_string.CONFIG_ROOTDIR, root_dir)

    leaf_error = leafcore_instance.a_update()
    if(leaf_error != 0):
        blog.error("Leaf error code: {}".format(leaf_error))
        blog.error("Failed to update cross root. Cannot continue.")
        return -1

    leaf_error = leafcore_instance.a_upgrade([])
    if(leaf_error != 0):
        blog.error("Leaf error code: {}".format(leaf_error))
        blog.error("Failed to upgrade cross root. Cannot continue")
        return -1
    
    leafcore_instance.clear_log()


def upgrade_real_root():
    root_dir = os.path.join(LAUNCH_DIR, "realroot")
    global leafcore_instance

    leafcore_instance.setStringConfig(LeafConfig_string.CONFIG_ROOTDIR, root_dir)

    leaf_error = leafcore_instance.a_update()
    if(leaf_error != 0):
        blog.error("Leaf error code: {}".format(leaf_error))
        blog.error("Failed to update real root. Cannot continue.")
        return -1

    leaf_error = leafcore_instance.a_upgrade([])
    if(leaf_error != 0):
        blog.error("Leaf error code: {}".format(leaf_error))
        blog.error("Failed to upgrade real root. Cannot continue")
        return -1

    leafcore_instance.clear_log()

    

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
