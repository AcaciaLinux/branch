import uuid
import blog
from packagebuild import package_build

class Job():

    def __init__(self, use_crosstools: bool, pkg_payload: package_build, requesting_client: str, solution_mode: bool = False):
        """
        Initialize a new Job

        :param use_crosstools: Use the 'CROSS' environment to build
        :param solution_mode: (Optional) Skip dependency resolver
        """

        uid = uuid.uuid4();
        blog.debug("Initializing new job with uuid: {}".format(str(uid)))
        self.id = str(uid)

        self.use_crosstools: bool = use_crosstools
        self.solution_mode: bool = solution_mode
        self.pkg_payload: package_build = pkg_payload
        self.requesting_client: str = requesting_client
        self.set_status("WAITING")

        self.buildbot = None
        self.blocked_by: list = [ ] 

        # [OVERWATCH] Check if job got accepted
        self.job_accepted = False

    def get_info_dict(self) -> dict:
        """
        Get information as a dictionary
        """
        return {
            "job_id": self.id,
            "job_status": self.job_status,
            "job_name": self.pkg_payload.name,
            "requesting_client": self.requesting_client
        }

    def get_jobid(self) -> str:
        """
        Get the current jobs id
        """
        return self.id

    def set_status(self, status: str):
        """
        Set the current jobs status
        """
        self.job_status = status

    def get_status(self) -> str:
        """
        Get the current jobs status
        """
        return self.job_status
    
    def set_buildlog(self, log: list):
        """
        Set the jobs buildlog
        """
        self.build_log = log
    
    def get_buildlog(self) -> list:
        """
        Get job build log
        """
        return self.build_log
    
    def set_running_buildbot(self, buildbot):
        """
        Set the buildbot (client) the job is running on
        """
        self.buildbot = buildbot
