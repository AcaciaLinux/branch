from log import blog
import uuid

class jobs():

    job_status = ""
    job_completed = False
    job_id = ""
    client = None

    def __init__(self):
        uid = uuid.uuid4();
        blog.debug("Initializing new job with uuid: {}".format(str(uid)))
        self.job_id = str(uid)
  
    def get_jobid(self):
        return self.job_id

    def set_status(self, status):
        self.job_status = status

    def get_status(self, status):
        return self.job_status

    def set_completed(self):
        self.job_completed = True

