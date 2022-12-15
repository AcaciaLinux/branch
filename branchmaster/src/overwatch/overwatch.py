# watches over buildbots
import time
from _thread import *
from log import blog
import threading

# Wait time in seconds for a buildbot response
ACCEPTED_TIMEOUT=5

#
# checks if buildbot answered in time
#
def check_accepted_timeout(manager, client, job):
    blog.debug("Overwatch watching client..")
    start_new_thread(check_accepted_timeout_thread, (manager,client,job))
    

def check_accepted_timeout_thread(manager, client, job):
    global ACCEPTED_TIMEOUT
    blog.debug("Waiting for response from buildbot..")
    time.sleep(ACCEPTED_TIMEOUT)
    if(job.job_accepted):
        blog.debug("Job accepted. Overwatch thread exiting.")
        return
    
    blog.warn("No acknowledgement received from buildbot. Attempting to resend build command to buildbot..")
    client.failed_commands += 1
    manager.get_queue().submit_build_cmd(client, job)
    blog.debug("Waiting for response from buildbot..")
    time.sleep(ACCEPTED_TIMEOUT)
    if(job.job_accepted):
        blog.debug("Job accepted. Overwatch thread exiting.")
        return
    
    blog.info("No response from buildbot received.")
    blog.warn("Buildbot failed. Closing connection..")
    client.handle_disconnect()
    return
