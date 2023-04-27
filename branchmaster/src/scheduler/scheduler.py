import blog
from manager.job import Job
from overwatch import overwatch
from branchpacket import BranchRequest

class BranchScheduler():

    def schedule(self):
        """
        Fetches a queued_job from managers BranchQueue,
        and calls submit() for every job
        """
        from manager.manager import Manager
        available_jobs: list = Manager.get_queue().get_available_jobs()
        available_buildbots: list = Manager.get_ready_build_clients()

        if(len(available_jobs) == 0):
            blog.info("Attempted to schedule Jobs, but there are no queued jobs.")
            return

        if(len(available_buildbots) == 0):
            blog.info("Attempted to schedule Jobs, but there are no buildbots available.")
            return

        for job in available_jobs:
            self.submit(job)

    def submit(self, job: Job) -> bool:
        """
        Submit a job to the fastest buildbot

        :param job: Job object
        """
        from manager.manager import Manager
        available_buildbots: list = Manager.get_ready_build_clients()

        if(len(available_buildbots) == 0):
            return False
        
        Manager.get_queue().notify_job_started(job)

        fastest_buildbot = min(available_buildbots, key=lambda x: x.get_sysinfo()["Performance Rating"])
        blog.info("Determined fastest buildbot '{}' with rating '{}'".format(fastest_buildbot.get_identifier(), fastest_buildbot.get_sysinfo()["Performance Rating"]))

        # buildbot is no longer ready.
        fastest_buildbot.is_ready = False        
        blog.info("Build job '{}' from '{}' submitted.".format(job.id, job.requesting_client))
        
        # assign our client to the job
        job.set_running_buildbot(fastest_buildbot)

        if(job.use_crosstools):
            fastest_buildbot.send_command(BranchRequest("BUILD", {
                "pkgbuild": job.pkg_payload.get_dict(),
                "buildtype": "CROSS"
            }))
        else:
            fastest_buildbot.send_command(BranchRequest("BUILD", {
                "pkgbuild": job.pkg_payload.get_dict(),
                "buildtype": "RELEASE"
            }))

        blog.info(f"Spawning overwatch thread for '{fastest_buildbot.get_identifier()}'")
        overwatch.check_accepted_timeout(fastest_buildbot, job)
        return True
