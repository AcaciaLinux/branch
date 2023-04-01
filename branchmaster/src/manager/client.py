import uuid
import blog
import traceback
import time

from manager import manager
from handleCommand import handleCommand
from threading import Lock

class Client():

    def __init__(self, socket):
        """
        Initialize a new client object
        :param socket: Client Socket
        :return: Client Object
        """
        
        # TODO: Which of these are actually needed..?
        # Better data structure?

        # file transfer mode
        self.file_transfer_mode: bool = False
        self.file_target_bytes: int = 0
        self.file_target: str = None

        # controller or build
        self.client_type = None

        # clear name to identify in log
        self.client_name = None
      
        # is authenticated
        self.is_authenticated = False

        # assign client a uuid
        uid = uuid.uuid4();
        blog.debug("Initializing new client with UUID: {}".format(str(uid)))
        self.client_uuid = uid

        # client socket
        self.socket = socket

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

    def set_sysinfo(self, info: dict):
        """
        Set buildbot system information dictionary.
        :param info: Client system info
        """
        
        self.sysinfo: dict = info 

    def get_sysinfo(self) -> dict:
        """
        Get client system information
        :return: Get system info dict
        """

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

    def receive_command(self, data):
        """
        Receive command from a connected client.
        
        :param data: Raw data from the client as str
        :return: Response from the server
        """

        blog.debug("Command received from client '{}': {}".format(self.get_identifier(), data))
        
        # TODO: refactor with BranchPacket(?)

        res = None
        try:
            res = handleCommand.handle_command(manager.manager(), self, data)
        except Exception as ex:
            manager.manager.report_system_event("Branchmaster", "Exception raised while handling client command. Traceback: {}".format(ex))
            blog.debug("An endpoint handler function raised an exception:")
            blog.debug("Traceback:")
            traceback.print_exc()
            res = "EXCEPTION_RAISED"
        
        return res
    
    def set_identifier(self, name: str):
        """
        Sets the clients clear name identifier

        :param name: Name as str
        """

    def get_identifier(self) -> str:
        """
        Fetches the clients current identifier if it's available,
        otherwise returns the client UUID

        :return: Current identifier 
        """

        if(self.client_name == None):
            return self.client_uuid
        else:
            return self.client_name

    def send_command(self, message):
        """
        Acquires the client lock and sends a command to the client
        
        :param message: The message to send
        """

        self.lock.acquire()
        message = "{} {}".format(len(message), message)
        self.socket.send(bytes(message, "UTF-8"))
        blog.debug("Message {} sent!".format(message))
        self.lock.release()
    
    def send_data(self, blob):
        """
        Acquires the client lock and sends bytes to the client

        :param blob: bytes to send
        """
        
        self.lock.acquire()
        self.socket.send(blob)
        self.lock.release()

    def handle_disconnect(self):
        """
        Acquires the client lock, removes the client from
        the manager and closes the socket
        """

        self.lock.acquire()
        
        try:
            blog.info("Client {} has disconnected.".format(self.get_identifier()))
            manager.manager.remove_client(self)
            self.socket.close()
            self.alive = False
        except Exception:
            blog.debug("Dead client socket finally closed.")

        self.lock.release()
