import uuid
import blog
import traceback
import time

from manager import manager
from threading import Lock

class Client():

    def __init__(self, sock):
        # uuid
        self.client_uuid = None

        # controller or build
        self.client_type = None

        # clear name to identify in log
        self.client_name = None

        # file transfer mode
        self.file_transfer_mode = False

        # is authenticated
        self.is_authenticated = False

        # assign client a uuid
        uid = uuid.uuid4();
        blog.debug("Initializing new client with UUID: {}".format(str(uid)))
        self.client_uuid = uid

        # client socket
        self.sock = sock

        # client is not ready by default
        self.is_ready = False

        # number of failed commands (incremented by overwatch) 
        self.failed_commands = 0
        
        # client alive flag
        self.alive = True

        # thread lock
        self.lock = Lock()

        # register the client
        manager.manager.register_client(self)

        # connected at
        self.connection_start_timestamp = time.time()

    
    #
    # Set buildbot provided system info
    #
    def set_buildbot_sysinfo(self, info):
        self.sysinfo = info 

    #
    # Get system info
    #
    def get_sysinfo(self):
        sys_info = { }
        sys_info["Connection timestamp"] = self.connection_start_timestamp
        
        if(self.client_type == "BUILD"):
            sys_info["Timed out commands [recovered]"] = self.failed_commands

        try:
            for attr in self.sysinfo:
                sys_info[attr] = self.sysinfo[attr]
        except AttributeError:
            pass

        return sys_info

    #
    # receive data from manager
    #
    def receive_command(self, data):
        res = None
        try:
            res = manager.manager.handle_command(self, data)
        except Exception as ex:
            manager.manager.report_system_event("Branchmaster", "Exception raised while handling client command. Traceback: {}".format(ex))
            blog.debug("An endpoint handler function raised an exception:")
            blog.debug("Traceback:")
            traceback.print_exc()
            res = "EXCEPTION_RAISED"
        
        return res

    #
    # Get the clients identifier
    # UUID by default, can be changed by command
    #
    def get_identifier(self):
        if(self.client_name == None):
            return self.client_uuid
        else:
            return self.client_name

    #
    # send_command to self
    #
    def send_command(self, message):
        self.lock.acquire()
        message = "{} {}".format(len(message), message)
        self.sock.send(bytes(message, "UTF-8"))
        blog.debug("Message {} sent!".format(message))
        self.lock.release()

    #
    # handle a clients disconnect.
    #
    def handle_disconnect(self):
        self.lock.acquire()
        
        try:
            blog.info("Client {} has disconnected.".format(self.get_identifier()))
            manager.manager.remove_client(self)
            self.sock.close()
            self.alive = False
        except Exception:
            blog.debug("Dead client socket finally closed.")

        self.lock.release()
