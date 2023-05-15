from manager.job import Job
from dependency import dependency
import blog

class BranchQueue():

    def __init__(self):
        self.queued_jobs    = [ ]
        self.running_jobs   = [ ]
        self.completed_jobs = [ ]

    # create a new Job object
    def add_job(self, job: Job):
        """
        Adds a JOB to the queue
        and checks if it should be "BLOCKED"
        or "WAITING"
        """
        self.queued_jobs.append(job)
        self.update_job_blocking()

    def add_jobs(self, jobs: list):
        self.queued_jobs.extend(jobs)
        self.update_job_blocking()

    def update_job_blocking(self):
        """
        Update job blocking for queued jobs
        """
        for job in self.queued_jobs:
            #
            # If the job is in solution mode, do not recalculate blockers.
            #
            if(job.solution_mode):
                blog.debug("Job is in solution mode. Keeping explicitly defined job-blocking.")
                job.set_status("WAITING")

                for blocker in job.blocked_by:
                    if(any(queued_job.id == blocker for queued_job in self.queued_jobs)):
                        blog.debug("Job '{}' ({}) is blocked by queued job defined in solution.".format(job.pkg_payload.name, job.id))
                        job.set_status("BLOCKED")
                        break
            
            #
            # If the job is not in solution mode, calculate blockers
            #
            else:
                blog.info("Job is not in solution mode, calculating blockers..")
                job.blocked_by = [ ]
                
                # Select the correct dependency array
                if (job.use_crosstools):
                    dependencies = job.pkg_payload.cross_dependencies
                else:
                    dependencies = job.pkg_payload.build_dependencies


                # The queued jobs
                for job_found in dependency.package_dep_in_queue(self.queued_jobs, dependencies):
                    blog.debug("Job '{}' ({}) is blocked by queued job '{}' ({})".format(job.pkg_payload.name, job.id, job_found.pkg_payload.name, job_found.id))
                    job.blocked_by.append(job_found.id)

                # The running jobs
                for job_found in dependency.package_dep_in_queue(self.running_jobs, dependencies):
                    blog.debug("Job '{}' ({}) is blocked by running job '{}' ({})".format(job.pkg_payload.name, job.id, job_found.pkg_payload.name, job_found.id))
                    job.blocked_by.append(job_found.id)

                # Finished and "COMPLETED" jobs
                for job_found in dependency.package_dep_in_queue(self.completed_jobs, dependencies):
                    if (job_found.get_status() != "COMPLETED"):
                        blog.debug("Job '{}' ({}) is blocked by failed job '{}' ({}) [{}]".format(job.pkg_payload.name, job.id, job_found.pkg_payload.name, job_found.id, job_found.get_status()))
                        job.blocked_by.append(job_found.id)

                if (len(job.blocked_by) > 0):
                    job.set_status("BLOCKED")
                else:
                    job.set_status("WAITING")
        
    
    def get_available_jobs(self) -> list:
        """
        Fetch available jobs for execution

        :return: list of available jobs
        """
        available_jobs = [ ]

        for job_to_execute in self.queued_jobs:
            job_is_blocked: bool = False

            for queued_job in self.running_jobs:
                if(queued_job.id in job_to_execute.blocked_by):
                    job_is_blocked = True

            for running_job in self.running_jobs:
                if(running_job.id in job_to_execute.blocked_by):
                    job_is_blocked = True

            if(not job_is_blocked):
                available_jobs.append(job_to_execute)

        return available_jobs
    
    def get_blocked_jobs(self) -> list:
        """
        STUB!
        Fetch blocked jobs that cannot be executed
        
        :return: list of blocked jobs
        """
        # TODO: implement this
        pass


    def get_running_job_by_client(self, client) -> Job:
        """
        Get a running job by handling client

        :param client: Client to search for
        :return: Job or None
        """
        for running_job in self.running_jobs:
            if(running_job.buildbot == client):
                return running_job
            
        return None

    def get_job_by_id(self, id: str) -> Job:
        """
        Get a job by id from {queued, running, completed} jobs

        :param id: JobID
        :return: Job or None
        """
        for job in self.running_jobs:
            if(job.id == id):
                return job
        for job in self.queued_jobs:
            if(job.id == id):
                return job

        for job in self.completed_jobs:
            if(job.id == id):
                return job
            
        return None

    def notify_job_started(self, job: Job) -> bool:
        """
        Move job from queued_jobs to running jobs
        queued_jobs -> running_jobs

        :param job: Job object
        :return: bool success
        """
        if(not job in self.queued_jobs):
            return False

        self.queued_jobs.remove(job)
        self.running_jobs.append(job)
        self.update_job_blocking()
        return True

    def notify_job_aborted(self, job: Job) -> bool:
        """
        Job aborted because builbot died
        running_jobs -> queued_jobs [head]

        :param job: Job object
        :return: bool success
        """
        if(not job in self.running_jobs):
            return False

        self.running_jobs.remove(job)
        job.set_status("WAITING")
 
        # push to head of list
        self.queued_jobs = [ job ] + self.queued_jobs

        self.update_job_blocking()
        return True

    def notify_job_completed(self, job: Job) -> bool:
        """
        Job completed
        running_jobs -> completed_jobs
        """
        if(not job in self.running_jobs):
            return False
        
        self.running_jobs.remove(job)
        self.completed_jobs.append(job)

        self.update_job_blocking()
        return True

    def get_queued_jobs(self) -> list:
        """
        Get all queued jobs
        """
        return self.queued_jobs
        
    def get_running_jobs(self) -> list:
        """
        Get all running jobs
        """
        return self.running_jobs

    def get_completed_jobs(self) -> list:
        """
        Get all completed jobs
        """
        return self.completed_jobs
    
    def clear_completed_jobs(self):
        """
        Clear the completed job list
        """
        self.completed_jobs = [ ]
        self.update_job_blocking()

    def cancel_queued_job(self, id: str) -> bool:
        """
        Cancel a queued job by ID

        :param id: Job ID
        :return: bool, True if cancelled, False if no such job  
        """

        job = self.get_job_by_id(id)

        if(job is None):
            return False

        self.queued_jobs.remove(job)
        self.update_job_blocking()
        return True


    def cancel_queued_jobs(self):
        """
        Cancel all queued jobs
        """
        self.queued_jobs = [ ]
