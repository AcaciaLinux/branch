from log import blog
import uuid

class jobs():

    job_completed = False
    job_id = ""
    build_pkg_name = ""
    requesting_client = ""
    client = None
    job_status = ""
    
    def __init__(self):
        uid = uuid.uuid4();
        blog.debug("Initializing new job with uuid: {}".format(str(uid)))
        self.job_id = str(uid)

    def get_info_dict(self):
        return {
            "job_id": self.job_id,
            "job_status": self.job_status,
            "build_pkg_name": self.build_pkg_name,
            "requesting_client": self.requesting_client
        }

    def get_jobid(self):
        return self.job_id

    def set_status(self, status):
        self.job_status = status

    def get_status(self, status):
        return self.job_status

    def set_completed(self):
        self.job_completed = True

