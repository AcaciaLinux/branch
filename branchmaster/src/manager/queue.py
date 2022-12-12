import json

from manager import manager
from log import blog
from package import build
from dependency import dependency

class queue():
    
    # static manager object
    def __init__(self, mgr):
        self.manager = mgr
        
    #
    # Check if job is blocked
    #
    def job_is_blocked(self, job):
        for blocker in job.blocked_by:
            sjob = self.manager.get_job_by_id(blocker)
            if(not sjob in self.manager.completed_jobs):
                blog.debug("Job is currently blocked: {}".format(job.build_pkg_name))
                return True
            else:
                return False

    #
    # Called when a controller requests RELEASE_BUILD
    #
    def add_to_queue(self, job):
        
        # We have a build server ready immediately, no need to queue..
        if(not len(self.manager.get_ready_build_clients()) == 0):
            blog.info("Build request was immediately handled by a ready build client.")
            clients = self.manager.get_ready_build_clients()
        
            # get first ready build client, and submit
            cli = clients[0]
            self.submit_build_cmd(cli, job)
 
            self.manager.queued_jobs.remove(job)
            self.manager.build_jobs.append(job)


            return "BUILD_REQ_SUBMIT_IMMEDIATELY"
        # We dont have a build server ready, we need to queue..
        else:
            blog.info("No build clients are currently available. Package submitted to queue.")
            return "BUILD_REQ_QUEUED"

    #
    # Called when we get SIG_READY from buildbot
    #
    def notify_ready(self):
        # no queue, idle bot..
        if(not self.manager.queued_jobs):
            blog.debug("A build client is ready, but is currently not needed.")
            return

        blog.debug("A build client is ready to accept build jobs. Submitting immediately.")

        job = None
        unblocked_jobs = [ ]

        # find not blocked jobs
        for sjob in self.manager.queued_jobs:
            if(not self.job_is_blocked(sjob)):
                unblocked_jobs.append(sjob)
       
        # Notify that there are no jobs available
        if(not unblocked_jobs):
            blog.info("No job available for client. All jobs are blocked or none is waiting.")
            return

        # find idle buildbots
        for ready_client in self.manager.get_ready_build_clients():
            # break if we have no unblocked jobs
            if(not unblocked_jobs):
                break

            # get an unblocked job
            job = unblocked_jobs.pop()

            # remove job from queued, add to building
            self.manager.queued_jobs.remove(job)
            self.manager.build_jobs.append(job)

            blog.debug("Submitting job to a ready buildbot.")
            self.submit_build_cmd(ready_client, job)


    def submit_build_cmd(self, client, job_obj):
        client.is_ready = False        
    
        # our jobs id
        job_id = job_obj.job_id

        blog.info("Build job '{}' from '{}' submitted.".format(job_id, job_obj.requesting_client))
        
        # assign our client to the job, state: INIT
        job_obj.client = client

        # get json str of package
        pkg_json = json.dumps(job_obj.pkg_payload.__dict__)

        # assign pkg_name and our client name to the job
        client.is_ready = False

        if(job_obj.use_crosstools):
            client.send_command("BUILD_PKG_CROSS {}".format(pkg_json))
        else:    
            client.send_command("BUILD_PKG {}".format(pkg_json))

