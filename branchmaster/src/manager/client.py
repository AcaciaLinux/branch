import uuid
import blog
import traceback
import time

from json.decoder import JSONDecodeError
from manager import manager
from threading import Lock
from branchpacket import BranchRequest, BranchResponse, BranchStatus
from commands import commands

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

        # CONTROLLER, BUILD or UNTRUSTED
        self.client_type = "UNTRUSTED"

        # clear name to identify in log
        self.client_name = None
      
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
        
        try:
            request = BranchRequest.from_json(data)

        # Fail if the client doesn't send a valid BranchPacket.
        except JSONDecodeError:
            response = BranchResponse(BranchStatus.REQUEST_FAILURE, "Invalid command received. Your client may be out of date or the request was malformed.")
            return response.as_json()
        
        try:
            res: BranchResponse = commands.handle_command(self, request)

            if(res == None):
                return None

        except Exception as ex:
            manager.manager.report_system_event("Branchmaster", "Exception raised while handling client command. Traceback: {}".format(ex))
            blog.debug("An endpoint handler function raised an exception:")
            blog.debug("Traceback:")
            traceback.print_exc()
            res: BranchResponse = BranchResponse(BranchStatus.INTERNAL_SERVER_ERROR, "An endpoint handler function raised an exception on the server. Please report this issue to the servers administrator. If you have access to the servers log, consider filing an issue on GitHub.")
        
        return res.as_json()

    
    def set_identifier(self, name: str) -> bool:
        """
        Sets the clients clear name identifier

        :param name: Name as str
        :return: True, if identifier is valid, False if not
        """

        if(name is None or name == ""):
            return False
        
        self.client_name = name
        return True 

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


    def set_type(self, machine_type) -> bool:
        """
        Set the client type to either CONTROLLER or BUILD

        :return: True if the type is valid, False if it's invalid.
        """
        if(machine_type == "CONTROLLER" or machine_type == "BUILD"):
            self.client_type = machine_type
            return True

        return False

    def send_command(self, message: BranchRequest):
        """
        Acquires the client lock and sends a command to the client
        
        :param message: The message to send
        """

        self.lock.acquire()
        message = "{} {}".format(len(message.as_json()), message.as_json())
        self.socket.send(bytes(message, "UTF-8"))
        self.lock.release()
    
    def send_data(self, blob):
        """
        Acquires the client lock and sends bytes to the client

        :param blob: bytes to send
        """
        
        self.lock.acquire()
        self.socket.send(blob)
        self.lock.release()

    def receive_file(self):
        """
        Receive a file from a client

        :param client: A Client object
        """

        if(self.file_target == None):
            blog.error("No file target set, but the client was set to filetransfer mode. Aborting.")
            self.file_transfer_mode = False
            return

        with open(self.file_target, "wb") as out_file:
            data_len = 0
            blog.info("File transfer started from {}. Receiving {} bytes from client..".format(self.get_identifier(), self.file_target_bytes))
            
            while(not self.file_target_bytes == data_len):
                data = self.socket.recv(4096)
                if(data == b""):
                    break

                data_len += len(data)
                out_file.write(data)
            
            if(data_len == self.file_target_bytes):
                blog.info("Received {} bytes. File upload successful".format(self.file_target_bytes))
                self.send_command(BranchResponse(BranchStatus.OK, "File transfer completed."))
                blog.info("File upload completed.")
            else:
                blog.warn("File upload failed. The client disconnected before completion.")
                
            self.file_transfer_mode = False
        


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
