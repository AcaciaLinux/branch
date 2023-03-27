import json
import blog

from manager import manager
from dependency.dependency import update_blockages
from overwatch import overwatch

class queue():
    
    #
    # Check if job is blocked
    #
    def job_is_blocked(self, job):
        return job.get_status() == "BLOCKED"

    #
    # Called when a controller requests BUILD
    #
    def add_to_queue(self, job):
        if(self.job_is_blocked(job)):
            blog.debug("Job is blocked, adding to queue..")
            return "BUILD_REQ_QUEUED"

        # We have a build server ready immediately, no need to queue..
        if(not len(manager.manager.get_ready_build_clients()) == 0):
            blog.info("Build request was immediately handled by a ready build client.")
            clients = manager.manager.get_ready_build_clients()
        
            # get first ready build client, and submit
            fastest_client = clients[0]
    
            for client in clients:
                sysinfo = client.get_sysinfo()
                
                # give bots that dont run the perf test a very high rating
                perf_rating = 100

                if("Performance Rating" in sysinfo):
                    perf_rating = sysinfo["Performance Rating"]
                
                fastest_client_sysinfo = fastest_client.get_sysinfo()

                # give bots that dont run the perf test a very high rating
                fastest_perf_rating = 100
                if("Performance Rating" in fastest_client_sysinfo):
                    fastest_perf_rating = fastest_client_sysinfo["Performance Rating"]

                # next client is faster, use that one.
                if(perf_rating < fastest_perf_rating):
                    fastest_client = client
            
            blog.info("Determined fastest client '{}' with rating '{}'".format(fastest_client.get_identifier(), fastest_client.get_sysinfo()["Performance Rating"]))

            overwatch.check_accepted_timeout(fastest_client, job)
            self.submit_build_cmd(fastest_client, job)
 
            manager.manager.queued_jobs.remove(job)
            manager.manager.running_jobs.append(job)

            return "BUILD_REQ_SUBMIT_IMMEDIATELY"
        # We dont have a build server ready, we need to queue..
        else:
            blog.info("No build clients are currently available. Package submitted to queue.")
            return "BUILD_REQ_QUEUED"

    #
    # Updates the queue, this reevaluates blockages and dispatches jobs to buildbots
    #
    def update(self):
        blog.info("Updating queue...")

        # Recalculate blocked jobs
        update_blockages()

        # no queue, idle bot..
        if(not manager.manager.queued_jobs):
            blog.debug("A build client is ready, but is currently not needed.")
            return

        blog.debug("A build client is ready to accept build jobs. Submitting immediately.")

        job = None
        unblocked_jobs = [ ]

        # find not blocked jobs
        for sjob in manager.manager.queued_jobs:
            if(not self.job_is_blocked(sjob)):
                blog.debug("Job '{}' ({}) is able to be built now".format(sjob.pkg_payload.name, sjob.job_id))
                unblocked_jobs.append(sjob)

        # Notify that there are no jobs available
        if(not unblocked_jobs):
            if(len(manager.manager.queued_jobs) > 0):
                blog.error("STALL: Can't continue building, there are some jobs queued but they block eachother")
                manager.manager.report_system_event("queue", "STALL: All queued build jobs are blocked by eachother")
            else:
                blog.info("No job available for client.")
            return

        # find idle buildbots
        for ready_client in manager.manager.get_ready_build_clients():
            # break if we have no unblocked jobs
            if(not unblocked_jobs):
                break

            # get an unblocked job
            # get head of list
            job = unblocked_jobs[0]
            del unblocked_jobs[0]

            # remove job from queued, add to building
            manager.manager.queued_jobs.remove(job)
            manager.manager.running_jobs.append(job)

            blog.debug("Submitting job to a ready buildbot.")
            overwatch.check_accepted_timeout(ready_client, job)
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

