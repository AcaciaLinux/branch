from log import blog

from pathlib import Path
import os
import shutil

def check_buildenv():
    # 3 directories required for overlayFS
    root_dir = os.path.join(os.getcwd(), "realroot")
    diff_dir = os.path.join(os.getcwd(), "diffdir")
    work_dir = os.path.join(os.getcwd(), "overlay")
    temp_dir = os.path.join(os.getcwd(), "temproot")

    # control file exists if installed
    control_file = os.path.join(root_dir, "installed")

    if(os.path.exists(control_file)):
        setup_env(root_dir, diff_dir, work_dir, temp_dir)
    else:
        deploy_buildenv(root_dir, diff_dir, work_dir, temp_dir)

def deploy_buildenv(root_dir, diff_dir, work_dir, temp_dir):
    blog.info("Deploying build environment..")

    # check if paths exist..
    if(not os.path.exists(root_dir)):
        os.mkdir(root_dir)

    if(not os.path.exists(diff_dir)):
        os.mkdir(diff_dir)

    if(not os.path.exists(overlay_dir)):
        os.mkdir(overlay_dir)

    if(not os.path.exists(temp_dir)):
        os.mkdir(temp_dir)
    
    # pyleaf stub
    blog.warn("STUB: pyleaf call to install base system")

    # control_file
    Path(os.path.join(root_dir, "installed").touch()

    setup_env(root_dir, diff_dir, overlay_dir)

def setup_env(root_dir, diff_dir, overlay_dir, temp_dir):
    if(not Path(diff_dir).is_mount()):
        os.command("mount -t overlay overlay -o lowerdir={},upperdir={},workdir={} {}".format(root_dir, diff_dir, overlay_dir, temp_dir))

def clean_env():
    temp_dir = os.path.join(os.getcwd(), "temproot")
    diff_dir = os.path.join(os.getcwd(), "diffdir")
    os.command("umount {}".format(temp_dir)

    shutil.rmtree(diff_dir)
    os.mkdir(diff_dir)
    os.command("mount -t overlay overlay -o lowerdir={},upperdir={},workdir={} {}".format(root_dir, diff_dir, overlay_dir, temp_dir))
