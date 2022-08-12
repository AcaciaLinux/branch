import json

from log import blog
from package import build
from localstorage import localstorage

class queue():
    
    build_queue = [ ]

    def add_to_queue(self, manager, pkg_name, requesting_client):
        stor = localstorage.storage()
        pkg = stor.get_bpb_obj(pkg_name)

        if(pkg is None):
            return "INV_PKG"

        # We have a build server ready immediately, no need to queue..
        if(not len(manager.get_ready_build_clients()) == 0):
            blog.info("Build request was immediately handled by a ready build client.")
            clients = manager.get_ready_build_clients()
            cli = clients[0]
    
            self.submit_build_cmd(manager, cli, pkg, requesting_client.get_identifier())

            return "BUILD_REQ_SUBMIT_IMMEDIATELY"
        # We dont have a build server ready, we need to queue..
        else:
            blog.info("No build clients are currently available. Package submitted to queue.")
            
            # add the requesting client
            pkg.requesting_client = requesting_client.get_identifier()

            self.build_queue.append(pkg)
            return "BUILD_REQ_QUEUED"

    def notify_ready(self, manager):
        if(not self.build_queue):
            blog.debug("A build client is ready, but is currently not needed.")
            return

        blog.debug("A build client is ready to accept build jobs. Submitting immediately.")
        
        # submit package
        pkg = self.build_queue.pop()

        clients = manager.get_ready_build_clients()
        cli = clients[0]

        self.submit_build_cmd(manager, cli, pkg, pkg.requesting_client)


    def submit_build_cmd(self, manager, client, pkg, requesting_client):
        client.is_ready = False        

        # get a new job
        job_id = manager.new_job().job_id
        job_obj = manager.get_job_by_id(job_id)

        blog.info("Build job '{}' from '{}' submitted.".format(job_id, requesting_client))
        
        # assign our client to the job
        job_obj.client = client
        job_obj.set_status("INIT")

        pkg.job_id = job_id
        pkg_json = json.dumps(pkg.__dict__)

        # assign pkg_name and our client name to the job
        job_obj.build_pkg_name = pkg.name
        job_obj.requesting_client = requesting_client

        client.is_ready = False
        client.send_command("BUILD_PKG {}".format(pkg_json))
