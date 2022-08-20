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

        manager.static_manager.register_client(self)
        is_ready = False

    def receive_command(self, conn, mask):
        data = None

        try:
            data = conn.recv(8192)
        except ConnectionResetError:
            self.handle_disconnect()
            return

        data_str = data.decode("utf-8")
        data_str_loc = data_str.find(" ")
        cmd_bytes = 0

        data_trimmed = data_str[data_str_loc+1:len(data_str)]

        try:
            cmd_bytes = int(data_str[0:data_str_loc])
        except ValueError:
            blog.warn("Byte count error from '{}'. Kicking client.".format(self.get_identifier()))
            self.handle_disconnect()
            return

        while(len(data_trimmed) != cmd_bytes):
            data_trimmed += conn.recv(8192).decode("utf-8")
            
        if data_trimmed:
            blog.debug("Received Data from {}. Data: {}".format(self.client_uuid, data_trimmed)) 
            manager.static_manager.handle_command(self, data_trimmed)
        else:
            # we got no data, handle a client disconnect.
            self.handle_disconnect()
    
    def get_identifier(self):
        if(self.client_name == None):
            return self.client_uuid
        else:
            return self.client_name


    def send_command(self, message):
        message = "{} {}".format(len(message), message)

        self.sock.send(bytes(message, "UTF-8"))

    def handle_disconnect(self):
        blog.info("Client {} has disconnected.".format(self.get_identifier()))
        manager.static_manager.remove_client(self)
        self.sel.unregister(self.sock)
        self.sock.close()

