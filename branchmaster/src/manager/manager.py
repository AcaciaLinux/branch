from log import blog
from handleCommand import handleCommand 
from manager import queue

class manager():
    queue = queue.queue()
    client_array = [ ]
    
    def get_queue(self):
        return self.queue

    def registerClient(self, client):
        blog.info("Adding client to manager '{}'.".format(client.get_identifier()))
        self.client_array.append(client)

    def getClient(self, uuid):
        return self.client_array[uuid]

    def handleCommand(self, client, command):
        blog.debug("Handling command from '{}': {}".format(client.get_identifier(), command))
        res = handleCommand.handle_command(self, client, command)
        if(not res is None):
            client.send_command(res)

    def removeClient(self, client):
        blog.info("Removing client '{}' from manager.".format(client.get_identifier()))
        self.client_array.remove(client)

    def getControllerClients(self):
        res = [ ]
        for cl in self.client_array:
            if(cl.client_type == "CONTROLLER"):
                res.append(cl)
        return res


    def getBuildClients(self):
        res = [ ]
        for cl in self.client_array:
            if(cl.client_type == "BUILD"):
                res.append(cl)
        return res

    def getReadyBuildClients(self):
        build_clients = self.getBuildClients()
        res = [ ]
        for cl in build_clients:
            if(cl.is_ready):
                res.append(cl)
        return res

static_manager = None
static_manager = manager()
