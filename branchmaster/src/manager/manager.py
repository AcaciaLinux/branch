from log import blog
from handleCommand import handleCommand 

class manager():
    client_array = [ ]

    def registerClient(self, client):
        blog.info("Adding client to manager '{}'.".format(client.get_identifier()))
        self.client_array.append(client)

    def getClient(self, uuid):
        return self.client_array[uuid]

    def handleCommand(self, client, command):
        blog.debug("Handling command from '{}': {}".format(client.get_identifier(), command))
        res = handleCommand.handle_command(self, client, command)
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

static_manager = None
static_manager = manager()
