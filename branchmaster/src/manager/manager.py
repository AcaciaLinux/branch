from log import blog
from handleCommand import handleCommand 
from manager import queue
from manager import jobs

class manager():
    
    # static class objects
    queue = None

    def __init__(self):
        manager.queue = queue.queue(self) 

    client_array = [ ]
    
    build_jobs = [ ]
    completed_jobs = [ ]
    queued_jobs = [ ]

    system_events = [ ]

    def get_queue(self):
        return self.queue

    def register_client(self, client):
        blog.info("Adding client to manager '{}'.".format(client.get_identifier()))
        manager.client_array.append(client)

    def get_client(self, uuid):
        return manager.client_array[uuid]

    def handle_command(self, client, command):
        blog.debug("Handling command from '{}': {}".format(client.get_identifier(), command))
        res = handleCommand.handle_command(self, client, command)
        if(not res is None):
            return res

    def remove_client(self, client):
        job = self.get_job_by_client(client)

        if(job is not None):
            blog.warn("Build job '{}' failed because the build client disconnected.".format(job.get_jobid()))
            job.set_completed = True
            job.set_status("FAILED")
            self.move_inactive_job(job)

        blog.info("Removing client '{}' from manager.".format(client.get_identifier()))
        manager.client_array.remove(client)

    def get_controller_clients(self):
        res = [ ]
        for cl in manager.client_array:
            if(cl.client_type == "CONTROLLER"):
                res.append(cl)
        return res


    def get_build_clients(self):
        res = [ ]
        for cl in manager.client_array:
            if(cl.client_type == "BUILD"):
                res.append(cl)
        return res

    def get_ready_build_clients(self):
        build_clients = self.get_build_clients()
        res = [ ]
        for cl in build_clients:
            if(cl.is_ready):
                res.append(cl)
        return res

    
    def new_job(self, use_crosstools):
        job = jobs.jobs(use_crosstools)
        manager.queued_jobs.append(job)
        return job

    def add_job_to_queue(self, job):
        manager.queued_jobs.append(job)

    def move_inactive_job(self, job):
        manager.build_jobs.remove(job)
        manager.completed_jobs.append(job)

    
    def get_job_by_client(self, client):
        for job in manager.build_jobs:
            if job in manager.build_jobs:
                if(job.client == client):
                    return job

        return None

    def get_job_by_id(self, jid):
        
        for job in manager.build_jobs:
            if(job.job_id == jid):
                return job
        for job in manager.queued_jobs:
            if(job.job_id == jid):
                return job

        for job in manager.completed_jobs:
            if(job.job_id == jid):
                return job
        return None
    
    def get_queued_jobs(self):
        return manager.queued_jobs

    def get_running_jobs(self):
        return manager.build_jobs
   
    def get_completed_jobs(self):
        return manager.completed_jobs

    def get_controller_names(self):
        res = [ ]

        for client in manager.client_array:
            if(client.client_type == "CONTROLLER"):
                res.append(client.get_identifier())

        return res

    def clear_completed_jobs(self):
        manager.completed_jobs = None
        manager.completed_jobs = [ ]

    
    def cancel_queued_job(self, job):
        manager.queued_jobs.remove(job)

    def cancel_all_queued_jobs(self):
        manager.queued_jobs = [ ] 

    def get_buildbot_names(self):
        res = [ ]

        for client in manager.client_array:
            if(client.client_type == "BUILD"):
                res.append(client.get_identifier())

        return res
