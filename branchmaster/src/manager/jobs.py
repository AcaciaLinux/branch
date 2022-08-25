import uuid

from log import blog

class jobs():
    def __init__(self):

        # class members
        self.job_id = ""
        
        self.pkg_payload = None
        
        self.build_pkg_name = ""

        self.requesting_client = ""
        self.client = None
        self.job_status = ""
        self.blocked_by = [ ] 

        # ft mode
        self.file_name = None
        self.file_size = None

        uid = uuid.uuid4();
        blog.debug("Initializing new job with uuid: {}".format(str(uid)))
        self.job_id = str(uid)

    #
    # get dict of class variables
    # that are interesting
    #
    def get_info_dict(self):
        return {
            "job_id": self.job_id,
            "job_status": self.job_status,
            "build_pkg_name": self.build_pkg_name,
            "requesting_client": self.requesting_client
        }

    #
    # get current job's id
    #
    def get_jobid(self):
        return self.job_id

    #
    #  set job_status
    #
    def set_status(self, status):
        self.job_status = status

    #
    # get job status
    #
    def get_status(self):
        return self.job_status

