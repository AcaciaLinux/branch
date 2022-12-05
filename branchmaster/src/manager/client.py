import uuid

from log import blog
from manager import manager

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

        # register the client
        manager.manager().register_client(self)
        is_ready = False
  
    #
    # receive data from manager
    #
    def receive_command(self, data):
        return manager.manager().handle_command(self, data)

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
        blog.info("send_command function called.")
        message = "{} {}".format(len(message), message)
        self.sock.send(bytes(message, "UTF-8"))
        blog.info("Message {} sent!".format(message))

    #
    # handle a clients disconnect.
    #
    def handle_disconnect(self):
        blog.info("Client {} has disconnected.".format(self.get_identifier()))
        manager.manager().remove_client(self)
        self.sock.close()

