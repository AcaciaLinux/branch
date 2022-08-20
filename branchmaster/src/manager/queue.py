import json

from log import blog
from package import build
from localstorage import localstorage
from dependency import dependency

class queue():

    # We need to have our JOBS object 
    # always accessible.
    # think about tmrw
    # ````
    #TODO: fixed by requesting all jobs from manager

    def job_is_blocked(self, manager, job):
        for blocker in job.blocked_by:
            #job = dependency.get_job_by_id(blocker)
            sjob = manager.get_job_by_id(blocker)
            if(not sjob in manager.completed_jobs):
                print("Job is !blocked!: ", job.build_pkg_name)
                print("Blocked by: ")
                
                for b in job.blocked_by:
                    asdf = manager.get_job_by_id(b)
                    print(asdf.build_pkg_name)

                return True
            else:
                print("HERE: job is not blocked.")
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
            
            return "BUILD_REQ_SUBMIT_IMMEDIATELY"
        # We dont have a build server ready, we need to queue..
        else:
            blog.info("No build clients are currently available. Package submitted to queue.")
            return "BUILD_REQ_QUEUED"

    #
    # Called when we get SIG_READY from buildbot
    #
    def notify_ready(self, manager):
        if(not manager.queued_jobs):
            blog.debug("A build client is ready, but is currently not needed.")
            return

        blog.debug("A build client is ready to accept build jobs. Submitting immediately.")
       
        # iterate through queued_jobs, find one that is not blocked.
        # if it's blocked client waits.
        # how do we get back to this client and tell it that
        # after a job from a different client completes
        # we have new jobs unlocked

        #IDEA: find all jobs that were blocked by the job that just finished up
        #submit all unlocked jobs to waiting clients.
    
        #recheck_for_ready() ..?

        # Do we wait unecassarily with this approuch..?

        job = None
        d_unblocked_jobs = [ ]

        # find a not blocked package
        for sjob in manager.queued_jobs:
            if(not self.job_is_blocked(manager, sjob)):
                d_unblocked_jobs.append(sjob)
                blog.info("Found not blocked job: {}")
       

        print("All currently not blocked jobs:")
        for a in d_unblocked_jobs:
            print(a.build_pkg_name)


        # STUB? (IDEA)
        if(not d_unblocked_jobs):
            blog.info("No job available for client. All jobs are blocked or none is waiting.")
            return

        job = d_unblocked_jobs[0]
        
        manager.queued_jobs.remove(job)
        manager.build_jobs.append(job)

        clients = manager.get_ready_build_clients()
        cli = clients[0]

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
        client.send_command("BUILD_PKG {}".format(pkg_json))
