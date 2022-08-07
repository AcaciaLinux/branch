import json

from log import blog
from package import build
from localstorage import localstorage

class queue():
    
    build_queue = [ ]

    def add_to_queue(self, manager, pkg_name):
        stor = localstorage.storage()
        pkg = stor.get_bpb_obj(pkg_name)

        if(pkg is None):
            return "INV_PKG"

        # We have a build server ready immediately, no need to queue..
        if(not len(manager.get_ready_build_clients()) == 0):
            blog.info("Build request was immediately handled by a ready build client.")
            clients = manager.get_ready_build_clients()
            cli = clients[0]
    
            self.submit_build_cmd(manager, cli, pkg)

            return "BUILD_REQ_SUBMIT_IMMEDIATELY"
        # We dont have a build server ready, we need to queue..
        else:
            blog.info("No build clients are currently available. Package submitted to queue.")
            self.build_queue.append(pkg)
            return "BUILD_REQ_QUEUED"

    def notify_ready(self, manager):
        if(not self.build_queue):
            blog.info("A new build client is ready, but is currently not needed.")
            return

        blog.info("A new build client is ready to accept build jobs. Submitting immediately.")
        
        # submit package
        pkg = self.build_queue.pop()
       
        clients = manager.get_ready_build_clients()
        cli = clients[0]

        self.submit_build_cmd(manager, cli, pkg)


    def submit_build_cmd(self, manager, client, pkg):
        client.is_ready = False        

        # get a new job
        job_id = manager.new_job().job_id
        job_obj = manager.get_job_by_id(job_id)

        blog.info("Build job '{}' submitted.".format(job_id))
        
        # assign our client to the job
        job_obj.client = client
        job_obj.set_status("INIT")

        pkg.job_id = job_id
        pkg_json = json.dumps(pkg.__dict__)

        client.is_ready = False
        client.send_command("BUILD_PKG {}".format(pkg_json))
