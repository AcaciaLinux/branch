import time
import blog

from handleCommand import handleCommand 
from manager import queue
from manager import jobs

class manager():
    
    #
    # Static queue Object
    #
    queue = queue.queue()

    #
    # Currently connected clients
    #
    client_array = [ ]
    
    #
    # Queued, running and completed jobs 
    #
    queued_jobs = [ ]
    running_jobs = [ ]
    completed_jobs = [ ]
    
    #
    # Array of system Events
    #
    system_events = [ ]
    
    @staticmethod
    def get_queue():
        return manager.queue

    @staticmethod
    def register_client(client):
        blog.info("Adding client to manager '{}'.".format(client.get_identifier()))
        manager.client_array.append(client)
    
    @staticmethod
    def get_client(uuid):
        return manager.client_array[uuid]
    
    @staticmethod
    def get_client_by_name(name):
        for client in manager.client_array:
            if(client.get_identifier() == name):
                return client

        return None

    @staticmethod
    def handle_command(client, command):
        blog.debug("Handling command from '{}': {}".format(client.get_identifier(), command))
        res = handleCommand.handle_command(manager(), client, command)
        return res
    
    @staticmethod
    def remove_client(client):
        job = manager.get_job_by_client(client)

        if(job is not None):
            blog.warn("Build job '{}' aborted because the buildbot disconnected. Readding to head of queue..".format(job.get_jobid()))
            job.set_status("WAITING")
            manager.running_jobs.remove(job)
            manager.queued_jobs = [job] + manager.queued_jobs

        blog.info("Removing client '{}' from manager.".format(client.get_identifier()))
        manager.client_array.remove(client)

    @staticmethod
    def get_controller_clients():
        res = [ ]
        for cl in manager.client_array:
            if(cl.client_type == "CONTROLLER"):
                res.append(cl)
        return res

    @staticmethod
    def get_build_clients():
        res = [ ]
        for cl in manager.client_array:
            if(cl.client_type == "BUILD"):
                res.append(cl)
        return res
    
    @staticmethod
    def get_ready_build_clients():
        build_clients = manager.get_build_clients()
        res = [ ]
        for cl in build_clients:
            if(cl.is_ready):
                res.append(cl)
        return res

    @staticmethod 
    def new_job(use_crosstools):
        job = jobs.jobs(use_crosstools)
        manager.queued_jobs.append(job)
        return job

    @staticmethod
    def add_job_to_queue(job):
        manager.queued_jobs.append(job)
    
    @staticmethod
    def move_inactive_job(job):
        manager.running_jobs.remove(job)
        manager.completed_jobs.append(job)

    @staticmethod 
    def get_job_by_client(client):
        for job in manager.running_jobs:
            if job in manager.running_jobs:
                if(job.client == client):
                    return job

        return None
    
    @staticmethod
    def get_job_by_id(jid):
        for job in manager.running_jobs:
            if(job.job_id == jid):
                return job
        for job in manager.queued_jobs:
            if(job.job_id == jid):
                return job

        for job in manager.completed_jobs:
            if(job.job_id == jid):
                return job
        return None
    
    @staticmethod
    def get_queued_jobs():
        return manager.queued_jobs
    
    @staticmethod
    def get_running_jobs():
        return manager.running_jobs
    
    @staticmethod
    def get_completed_jobs():
        return manager.completed_jobs

    @staticmethod
    def get_controller_names():
        res = [ ]

        for client in manager.client_array:
            if(client.client_type == "CONTROLLER"):
                res.append(client.get_identifier())

        return res
    
    @staticmethod
    def clear_completed_jobs():
        manager.completed_jobs = None
        manager.completed_jobs = [ ]
        manager.get_queue().update()

    @staticmethod 
    def cancel_queued_job(job):
        manager.queued_jobs.remove(job)
        manager.get_queue().update()
    
    @staticmethod
    def cancel_all_queued_jobs():
        manager.queued_jobs = [ ] 
        manager.get_queue().update()
    
    @staticmethod
    def get_buildbot_names():
        res = [ ]

        for client in manager.client_array:
            if(client.client_type == "BUILD"):
                res.append(client.get_identifier())

        return res
    
    @staticmethod
    def report_system_event(issuer, event):
        current_time = time.strftime("%H:%M:%S %d-%m-%Y", time.localtime())
        manager.system_events.append("[{}] {} => {}".format(current_time, issuer, event))


