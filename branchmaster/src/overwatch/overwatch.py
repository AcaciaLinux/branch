import time
import blog

from _thread import *
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
    """
    Check if the given buildbot has started
    running the assigned Job. Reschedule the job
    if it isn't
    """
    from manager.manager import Manager
    global ACCEPTED_TIMEOUT

    blog.debug("Waiting for response from buildbot..")
    time.sleep(ACCEPTED_TIMEOUT)
    if(job.job_accepted):
        blog.debug("Job accepted. Overwatch thread exiting.")
        return
    
    blog.warn("No acknowledgement received from buildbot. Attempting to resend build command to buildbot..")
    client.failed_commands += 1
    Manager.report_system_event("Overwatch", "Buildbot '{}' did not respond. Continuing to wait..".format(client.get_identifier()))

    # abort job, reschedule..
    Manager.get_queue().notify_job_aborted(job)
    Manager.get_scheduler().schedule()

    blog.debug("Waiting for response from buildbot..")
    time.sleep(ACCEPTED_TIMEOUT)
    if(job.job_accepted):
        blog.debug("Job accepted. Overwatch thread exiting.")
        return
    
    blog.warn(f"Buildbot '{client.get_identifier()}' failed. Closing connection..")
    
    # report system event
    Manager.report_system_event("Overwatch", "Buildbot '{}' kicked by Overwatch (Reason: No response)".format(client.get_identifier()))
    blog.info(f"Buildbot '{client.get_identifier()}' kicked by Overwatch. (Reason: No response)")
    
    client.handle_disconnect()
    return

#
# periodically pings a buildbot to make sure it's alive.
#
def check_buildbot_alive(client):
    """
    Spawn a buildbot checker thread

    :param client: The client to ping
    """
    from manager.manager import Manager
    blog.info("Watching new buildbot '{}'. Acceptable response delay is {}s.".format(client.get_identifier(), ACCEPTED_TIMEOUT))
    Manager.report_system_event("Overwatch", "Watching new buildbot '{}'. Acceptable response delay is {} seconds.".format(client.get_identifier(), PING_PONG_TIME))
    start_new_thread(check_buildbot_alive_thread, (client,))

#
# check thread
#
def check_buildbot_alive_thread(client):
    """
    Periodically pings the given 'client',

    :param client: The client to ping
    """
    from manager.manager import Manager
    global PING_PONG_TIME
    
    while client.alive:
        # ping -> wait
        if(client.is_ready):
            blog.debug("Sending PING request to '{}'!".format(client.get_identifier()))
            client.is_ready = False
            client.alive = False
            client.send_command(BranchRequest("PING", ""))
            blog.debug("Awaiting response from '{}'..".format(client.get_identifier()))
        else:
            blog.debug("Client '{}' is busy. Skipping PING cycle.".format(client.get_identifier()))

        time.sleep(PING_PONG_TIME)
    
    blog.warn("Connection to '{}' lost.".format(client.get_identifier()))
    client.handle_disconnect()
    Manager.report_system_event("Overwatch", "Connection to '{}' lost. Disconnected.".format(client.get_identifier()))
    blog.info("Overwatch thread for client '{}' terminating.".format(client.get_identifier()))
