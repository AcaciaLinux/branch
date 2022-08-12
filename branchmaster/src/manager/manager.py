from log import blog
from handleCommand import handleCommand 
from manager import queue
from manager import jobs

class manager():
    queue = queue.queue()
    client_array = [ ]
    build_jobs = [ ]
    completed_jobs = [ ]

    def get_queue(self):
        return self.queue

    def register_client(self, client):
        blog.info("Adding client to manager '{}'.".format(client.get_identifier()))
        self.client_array.append(client)

    def get_client(self, uuid):
        return self.client_array[uuid]

    def handle_command(self, client, command):
        blog.debug("Handling command from '{}': {}".format(client.get_identifier(), command))
        res = handleCommand.handle_command(self, client, command)
        if(not res is None):
            client.send_command(res)

    def remove_client(self, client):
        blog.info("Removing client '{}' from manager.".format(client.get_identifier()))
        self.client_array.remove(client)

    def get_controller_clients(self):
        res = [ ]
        for cl in self.client_array:
            if(cl.client_type == "CONTROLLER"):
                res.append(cl)
        return res


    def get_build_clients(self):
        res = [ ]
        for cl in self.client_array:
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

    
    def new_job(self):
        job = jobs.jobs()
        self.build_jobs.append(job)
        return job

    def move_inactive_job(self, job):
        self.build_jobs.remove(job)
        self.completed_jobs.append(job)

    
    def get_job_by_client(self, client):
        for job in self.build_jobs:
            if job in self.build_jobs:
                if(job.client == client):
                    return job

    def get_job_by_id(self, jid):
        for job in self.build_jobs:
            if(job.job_id == jid):
                return job

        return None
     
    def get_running_jobs(self):
        return self.build_jobs
   
    def get_completed_jobs(self):
        return self.completed_jobs

static_manager = None
static_manager = manager()
