from log import blog
from localstorage import build
from localstorage import localstorage

class queue():
    
    build_queue = [ ]

    def add_to_queue(self, manager, pkg_name):
        stor = localstorage.storage()
        pkg_json = stor.get_json_bpb(pkg_name)

        if(pkg_json is None):
            return "INV_PKG"

        # We have a build server ready immediately, no need to queue..
        if(not len(manager.getReadyBuildClients()) == 0):
            blog.info("Build request was immediately handled by a ready build client.")
            clients = manager.getReadyBuildClients()
            cli = clients[0]
            cli.is_ready = False
            cli.send_command("BUILD_PKG {}".format(pkg_json))
            return "BUILD_REQ_SUBMIT_IMMEDIATELY"
        # We dont have a build server ready, we need to queue..
        else:
            blog.info("No build clients are currently available. Package submitted to queue.")
            self.build_queue.append(pkg_json)
            return "BUILD_REQ_QUEUED"

    def notify_ready(self, manager):
        if(not self.build_queue):
            blog.info("A build client notified it's ready, but is currently not needed.")
            return

        blog.info("A build client notified it's ready to accept builds.")
        
        # submit package
        blog.info("Submitting package to buildserver..")
        pkg = self.build_queue.pop()
       
        clients = manager.getReadyBuildClients()
        cli = clients[0]

        cli.is_ready = False
        cli.send_command("BUILD_PKG {}".format(pkg))
