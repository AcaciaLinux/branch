#
# Fake branch buildbot used for testing
# (performance and debugging)
#
# WARNING: DO NOT CONNECT THIS TO A PROD SERVER
# will upload garbage to the masterserver and not build anything!

UPLOAD_DATA=False
ALWAYS_STALL_UPLOAD=True

import random
import os
import socket
import time
import sys

def handshake(host, port, authkey):
    cltype = "BUILD"

    # connect to the server
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((host, port))
    except ConnectionRefusedError:
        print("Connection refused.")
        exit(-1)

    print("Connection established!")

    # send the authentication key if one is provided
    if(authkey is not None):
        print("Sending auth key..")
            
        cmd = "AUTH " + authkey
        cmd = "{} {}".format(len(cmd), cmd)

        s.sendall(bytes(cmd, "utf-8"))
        
        data = receive_data(s)
        
        if(data == "AUTH_OK"):
            print("Authkey accepted.")
        else:
            print("An error occured: {}".format(data))
            return None

    # send the machine type to the server
    print("Sending machine type..")
    cmd = "SET_MACHINE_TYPE " + cltype
    cmd = "{} {}".format(len(cmd), cmd)

    s.sendall(bytes(cmd, "utf-8"))
    data = receive_data(s)
    
    if(data == "CMD_OK"):
        print("Machine type granted.")
    else:
        print("An error occured: {}".format(data))
        return None

    # send the client name to the server
    print("Sending client name...")
    cmd = "SET_MACHINE_NAME FAKE_BOT_DO_NOT_USE"
    cmd = "{} {}".format(len(cmd), cmd)
    
    s.sendall(bytes(cmd, "utf-8"))
    data = receive_data(s)
    
    if(data == "CMD_OK"):
        print("Client name accepted.")
    else:
        print("An error occured: {}".format(data))
        return None

    return s

def receive_commands(s):
    print("Sending ready signal..")
    # send the "SIG_READY" message to the server
    msg = "SIG_READY"
    s.sendall(bytes("{} {}".format(len(msg), msg), "utf-8"))
    
    l = receive_data(s)


    print("Ready! Waiting for commands.")

    # enter a loop to continuously receive messages from the server
    while True:
        data = receive_data(s)
        handle_command_from_server(data, s)

def handle_command_from_server(command, s):
    # check if the received command is "BUILD_PKG"
    print(command)

    if command == "BUILD_PKG" or command == "BUILD_PKG_CROSS":
        print("Got a build job from the server!")

        # send the "BUILD_ENV_READY" message to the server
        print("Reporting status update: BUILD_ENV_READY")
        msg = "BUILD_ENV_READY"
        s.sendall(bytes("{} {}".format(len(msg), msg), "utf-8"))
        data = receive_data(s)

        # wait a few seconds
        #time.sleep(3)

        # send "BUILD_COMPLETE" to the server
        print("Reporting status update: BUILD_COMPLETE")
        msg = "BUILD_COMPLETE"
        s.sendall(bytes("{} {}".format(len(msg), msg), "utf-8"))
        data = receive_data(s)

        # wait a few seconds
        #time.sleep(3)
        
        print("Reading file length..")
        # send "FILE_TRANSFER_MODE {byte-len}" to the server
        with open("bla.bin", "rb") as f:
            byte_len = len(f.read())

        print("Reporting status update: FILE_TRANSFER_MODE")
        msg = "FILE_TRANSFER_MODE {}".format(byte_len)
        s.sendall(bytes("{} {}".format(len(msg), msg), "utf-8"))
        
        # check if the server acknowledged the file transfer mode
        print("Requesting mode switch..")
        data = receive_data(s)
        if data != "ACK_FILE_TRANSFER":
            print("Error: file transfer mode not acknowledged by the server.")
            return

        print("Server switched to FT-mode")

        # send the file to the server
        print("Uploading fakepackage..")

        fakepac = open("bla.bin", "rb")

        all_len = 0

        if UPLOAD_DATA:
            to_send = fakepac.read(4096)
            all_len = all_len + len(to_send)

            s.sendall(to_send)

        # TODO: fix this properly..
        if ALWAYS_STALL_UPLOAD:
            s.sendfile(open("bla.bin", "rb"))

        data = receive_data(s)

        # check if the server acknowledged the file upload
        if data != "UPLOAD_ACK":
            print("Error: file upload not acknowledged by the server.")
            return
        
        print("File upload acknowleged")

        print("Reporting status update: BUILD_CLEAN")
        msg = "BUILD_CLEAN"
        s.sendall(bytes("{} {}".format(len(msg), msg), "utf-8"))


        print("Reporting READY signal")
        msg = "SIG_READY"
        s.sendall(bytes("{} {}".format(len(msg), msg), "utf-8"))



# receive_data
def receive_data(sock):
    data = sock.recv(1024).decode("utf-8")
    
    #TODO: this will break for longer commands, fix?
    byte_len = data.split(" ")[0]
    data = data.split(" ")[1]

    return data

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

    print("FAKE BUILDBOT STARTING!")
    print("DEBUG PURPOSES ONLY!")
    print("DO NOT CONNECT THIS CLIENT TO A PRODUCTION SERVER!")
    print("Copyright (c) zimsneexh 2022 (https://zsxh.eu/)")

    #time.sleep(3)

    print("Generating random binary data to submit as package..")
    write_random_file()

    print("Picked up configuration: ")
    print("Host:", host)
    print("Port:", port)
    print("Authkey:", authkey)

    print("Handshaking..")
    s = handshake(host, int(port), authkey)
    
    print("Ready to receive commands!")
    receive_commands(s)

if __name__ == "__main__":
    main()
