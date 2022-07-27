from log import blog
from manager import manager
import uuid

class Client():
    # uuid
    client_uuid = None

    # controller or build
    client_type = None

    # clear name to identify in log
    client_name = None

    # socket and selector
    sock = None
    sel = None

    # ready boolean for build clients
    is_ready = None

    def __init__(self, sock, sel):
        uid = uuid.uuid4();
        blog.debug("Initializing new client with UUID: {}".format(str(uid)))
        self.client_uuid = uid
        
        self.sel = sel
        self.sock = sock

        manager.static_manager.registerClient(self)
        is_ready = False

    def receive_command(self, conn, mask):
        data = conn.recv(4096)
        if data:
            blog.debug("Received Data from {}. Data: {}".format(self.client_uuid, data)) 
            manager.static_manager.handleCommand(self, data)
        else:
            # we got no data, handle a client disconnect.
            self.handle_disconnect()
    
    def get_identifier(self):
        if(self.client_name == None):
            return self.client_uuid
        else:
            return self.client_name


    def send_command(self, message):
        self.sock.send(bytes(message, "UTF-8"))

    def handle_disconnect(self):
        blog.info("Client {} has disconnected.".format(self.get_identifier()))
        manager.static_manager.removeClient(self)
        self.sel.unregister(self.sock)
        self.sock.close()

