import json

from log import blog
from package import build
from dependency import dependency

class queue():

    #
    # Check if job is blocked
    #
    def job_is_blocked(self, manager, job):
        for blocker in job.blocked_by:
            sjob = manager.get_job_by_id(blocker)
            if(not sjob in manager.completed_jobs):
                blog.debug("Job is currently blocked: {}".format(job.build_pkg_name))
                return True
            else:
                return False

    #
    # Called when a controller requests RELEASE_BUILD
    #
    def add_to_queue(self, manager, job):
        
        # We have a build server ready immediately, no need to queue..
        if(not len(manager.get_ready_build_clients()) == 0):
            blog.info("Build request was immediately handled by a ready build client.")
            clients = manager.get_ready_build_clients()
        
            # get first ready build client, and submit
            cli = clients[0]
            self.submit_build_cmd(manager, cli, job)
 
            manager.queued_jobs.remove(job)
            manager.build_jobs.append(job)


            return "BUILD_REQ_SUBMIT_IMMEDIATELY"
        # We dont have a build server ready, we need to queue..
        else:
            blog.info("No build clients are currently available. Package submitted to queue.")
            return "BUILD_REQ_QUEUED"

    #
    # Called when we get SIG_READY from buildbot
    #
    def notify_ready(self, manager):

        # TODO: Fix!
        # If all jobs are blocked, but a new client is ready, it 
        # will not get a job assigned even after one became available.
        # implement a function which checks if there is a job available
        # for a waiting client
        
        #recheck_for_ready() ..?

        if(not manager.queued_jobs):
            blog.debug("A build client is ready, but is currently not needed.")
            return

        blog.debug("A build client is ready to accept build jobs. Submitting immediately.")

        job = None
        unblocked_jobs = [ ]

        # find a not blocked package
        for sjob in manager.queued_jobs:
            if(not self.job_is_blocked(manager, sjob)):
                unblocked_jobs.append(sjob)
       
        # Notify that there are no jobs available
        if(not unblocked_jobs):
            blog.info("No job available for client. All jobs are blocked or none is waiting.")
            return

        # get the first unblocked job
        job = unblocked_jobs[0]
        
        # remove job from queued, add to building
        manager.queued_jobs.remove(job)
        manager.build_jobs.append(job)

        # get a ready build client from the manager
        clients = manager.get_ready_build_clients()
        cli = clients[0]

        # submit the build command to the client
        self.submit_build_cmd(manager, cli, job)


    def submit_build_cmd(self, manager, client, job_obj):
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



