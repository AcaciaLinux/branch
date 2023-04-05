import time
import blog
import threading

from _thread import *
from manager import manager
from branchpacket import BranchRequest

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
    blog.warn("Buildbot {} failed. Closing connection..".format(client.get_identifier()))
    
    # report system event
    manager.manager.report_system_event("Overwatch", "Buildbot {} kicked by Overwatch (Reason: No response)".format(client.get_identifier()))
    blog.info("Buildbot {} kicked by Overwatch. (Reason: No response)".format(client.get_identifier()))
    
    client.handle_disconnect()
    return

#
# periodically pings a buildbot to make sure it's alive.
#
def check_buildbot_alive(client):
    blog.info("[Overwatch] Watching new buildbot '{}'. Acceptable response delay is {}s.".format(client.get_identifier(), ACCEPTED_TIMEOUT))
    manager.manager.report_system_event("Overwatch", "Watching new buildbot '{}'. Acceptable response delay is {} seconds.".format(client.get_identifier(), PING_PONG_TIME))
    start_new_thread(check_buildbot_alive_thread, (client,))

#
# check thread
#
def check_buildbot_alive_thread(client):
    global PING_PONG_TIME
    
    while client.alive:
        # ping -> wait
        if(client.is_ready):
            blog.debug("[Overwatch] Sending PING request to '{}'!".format(client.get_identifier()))
            client.is_ready = False
            client.alive = False
            client.send_command(BranchRequest("PING", ""))
            blog.debug("[Overwatch] Waiting for response from '{}'..".format(client.get_identifier()))
        else:
            blog.debug("[Overwatch] Client '{}' is busy. Skipping PING cycle.".format(client.get_identifier()))

        time.sleep(PING_PONG_TIME)
    
    blog.warn("[Overwatch] Connection to '{}' lost.".format(client.get_identifier()))
    client.handle_disconnect()
    manager.manager.report_system_event("Overwatch", "Connection to {} lost. Disconnected.".format(client.get_identifier()))
    blog.info("[Overwatch] Overwatch thread for client '{}' terminating.".format(client.get_identifier()))
