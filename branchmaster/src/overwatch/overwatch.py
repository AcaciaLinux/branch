import time
import blog
import threading

from _thread import *
from manager import manager

# Wait time in seconds for a buildbot response
ACCEPTED_TIMEOUT=5
# wait time in seconds before pinging a client again
PING_PONG_TIME=40

#
# checks if buildbot answered in time
#
def check_accepted_timeout(client, job):
    blog.debug("Overwatch watching client..")
    start_new_thread(check_accepted_timeout_thread, (client,job))
    
#
# check thread
#
def check_accepted_timeout_thread(client, job):
    global ACCEPTED_TIMEOUT
    blog.debug("Waiting for response from buildbot..")
    time.sleep(ACCEPTED_TIMEOUT)
    if(job.job_accepted):
        blog.debug("Job accepted. Overwatch thread exiting.")
        return
    
    blog.warn("No acknowledgement received from buildbot. Attempting to resend build command to buildbot..")
    client.failed_commands += 1
    manager.manager.get_queue().submit_build_cmd(client, job)
    blog.debug("Waiting for response from buildbot..")
    time.sleep(ACCEPTED_TIMEOUT)
    if(job.job_accepted):
        blog.debug("Job accepted. Overwatch thread exiting.")
        return
    
    blog.info("No response from buildbot received.")
    blog.warn("Buildbot failed. Closing connection..")
    
    # report system event
    manager.manager.report_system_event("Overwatch", "Buildbot {} kicked by Overwatch (Reason: No response)".format(client.get_identifier()))
    blog.info("Buildbot {} kicked by Overwatch. (Reason: No response)".format(client.get_identifier()))
    
    client.handle_disconnect()
    return

#
# periodically pings a buildbot to make sure it's alive.
#
def check_buildbot_alive(client):
    blog.debug("Overwatch checking if client {} is alive...".format(client.get_identifier()))
    start_new_thread(check_buildbot_alive_thread, (client,))

#
# check thread
#
def check_buildbot_alive_thread(client):
    global PING_PONG_TIME
    blog.debug("Watching {} ..".format(client.get_identifier()))
    
    while client.alive:
        # ping -> wait
        if(client.is_ready):
            blog.debug("Sending PING request to {}".format(client.get_identifier()))
            client.is_ready = False
            client.alive = False
            client.send_command("PING")
            blog.debug("Waiting for response from {}..".format(client.get_identifier()))
        else:
            blog.debug("Client is busy. Not pinging..")

        time.sleep(PING_PONG_TIME)
    
    blog.info("Buildbot {} disconnected.".format(client.get_identifier()))
    client.handle_disconnect()
    manager.manager.report_system_event("Overwatch", "Buildbot {} disconnected.".format(client.get_identifier()))
    blog.info("Overwatch thread exiting.")
