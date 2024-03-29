#
# Fake branch buildbot used for testing
# (performance and debugging)
#
# WARNING: DO NOT CONNECT THIS TO A PROD SERVER
# will upload garbage to the masterserver and not build anything!

UPLOAD_DATA=True
ALWAYS_STALL_UPLOAD=False
AUTO_RECONNECT=False
ALWAYS_IGNORE_COMMANDS=False

import platform
import psutil
import random
from branchpacket import BranchRequest, BranchResponse
from datetime import datetime
import os
import blog
import time
import sys
import branchclient

def cpu_test():
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

def get_host_info():
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

def handshake(host, port, authkey):
    return branchclient.branchclient(host, port, "FAKE_BOT", authkey, "BUILD")
    
def receive_commands(bc):
    data = bc.send_recv_msg(BranchRequest("GETDEPLOYMENTCONFIG", ""))
    print(data)

    blog.info("Sending ready signal..")
    data = bc.send_recv_msg(BranchRequest("SIGREADY", ""))
    blog.info("Ready! Waiting for commands.")
    
    if ALWAYS_IGNORE_COMMANDS:
        time.sleep(5000000)

    while True:
        data = bc.recv_branch_request()
        handle_command_from_server(data, bc)

def handle_command_from_server(command, bc):
    if command.command == "PING":
        bc.send_recv_msg(BranchRequest("PONG", ""))

    elif command.command == "BUILD_PKG" or command.command == "BUILD_PKG_CROSS":
        blog.info("Got a build job from the server!")

        # send the "BUILD_ENV_READY" message to the server
        blog.info("Reporting status update: BUILD_ENV_READY")
        data = bc.send_recv_msg(BranchRequest("REPORTSTATUSUPDATE", "JOB_ACCEPTED"))
        blog.info(data)
    
        # send the "BUILD_ENV_READY" message to the server
        blog.info("Reporting status update: BUILD_ENV_READY")
        data = bc.send_recv_msg(BranchRequest("REPORTSTATUSUPDATE", "BUILD_ENV_READY"))
        blog.info(data)

        # send "BUILD_COMPLETE" to the server
        blog.info("Reporting status update: BUILD_COMPLETE")
        data = bc.send_recv_msg(BranchRequest("REPORTSTATUSUPDATE", "BUILD_COMPLETE"))
        blog.info(data)

        blog.info("Reading file length..")

        blog.info("Reporting status update: FILE_TRANSFER_MODE {}".format(os.path.getsize("bla.bin")))
        data = bc.send_recv_msg(BranchRequest("FILETRANSFERMODE", os.path.getsize("bla.bin")))
        blog.info(data)

        blog.info("Server switched to FT-mode")

        # send the file to the server
        blog.info("Uploading fakepackage..")

        fakepac = open("bla.bin", "rb")

        all_len = 0
        
        f_u_res = ""

        if UPLOAD_DATA:
            blog.info("UPLOADING RANDOM BINARY DATA!")
            f_u_res = bc.send_file("bla.bin")
        
        # TODO: fix this properly..
        if ALWAYS_STALL_UPLOAD:
            blog.info("SET TO ALWAYS STALL UPLOAD!")
            time.sleep(500000)
        
        blog.info(f_u_res)
        

        # check if the server acknowledged the file upload
        #if f_u_res != "UPLOAD_ACK":
        #    blog.info("Error: file upload not acknowledged by the server.")
        #    return
        
        blog.info("File upload completed: UPLOAD_ACK")

        blog.info("Reporting status update: BUILD_CLEAN")
        data = bc.send_recv_msg(BranchRequest("REPORT_STATUS_UPDATE", "BUILD_CLEAN"))

        blog.info("Reporting READY signal")
        bc.send_recv_msg(BranchRequest("SIGREADY", ""))


# reads from stdin
def read_stdin():
	host = input("Enter the host: ")
	port = input("Enter the port: ")
	authkey = input("Enter the authkey: ")
	return host, port, authkey

def read_argv():
    host = sys.argv[1]
    port = int(sys.argv[2])
    authkey = sys.argv[3]
    return host, port, authkey

def write_random_file():
  # generate a random file size, up to 100 MB
  file_size = random.randint(1, 100 * 1024 * 1024)

  # generate random data of the specified size
  data = os.urandom(file_size)

  # write the data to the "bla.bin" file
  with open("bla.bin", "wb") as f:
    f.write(data)

def main():
    host = ""
    port = 0
    authkey = ""

    if(len(sys.argv) == 1):
        host, port, authkey = read_stdin()
    else:
        host, port, authkey = read_argv()

    blog.info("FAKE BUILDBOT STARTING!")
    blog.info("DEBUG PURPOSES ONLY!")
    blog.info("DO NOT CONNECT THIS CLIENT TO A PRODUCTION SERVER!")
    blog.info("Copyright (c) zimsneexh 2022 (https://zsxh.eu/)")
        
    blog.enable_debug_level()

    blog.info("Generating random binary data to submit as package..")
    write_random_file()

    blog.info("Picked up configuration: ")
    print("Host:", host)
    print("Port:", port)
    print("Authkey:", authkey)

    blog.info("Handshaking..")
    bc = None

    if AUTO_RECONNECT:
        while True:
            bc = handshake(host, int(port), authkey)
            if(bc == -1):
                time.sleep(20)
            else:
                break

    else:
        bc = handshake(host, int(port), authkey)
    
    blog.info("Ready to receive commands!")
    bc.send_recv_msg(BranchRequest("SETMACHINEINFORMATION", get_host_info()))
    receive_commands(bc)

if __name__ == "__main__":
    main()
