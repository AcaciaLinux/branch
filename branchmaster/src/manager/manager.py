import time
import blog
import requests
import hashlib
import shutil
import os
import packagebuild

from localstorage import packagestorage
from localstorage import pkgbuildstorage
from config import config
from manager import queue
from manager.job import Job

class manager():
    
    #
    # Static queue Object
    #
    queue = queue.queue()

    #
    # Currently connected clients
    #
    client_array = [ ]
    
    #
    # Queued, running and completed jobs 
    #
    queued_jobs = [ ]
    running_jobs = [ ]
    completed_jobs = [ ]
    
    #
    # Array of system Events
    #
    system_events = [ ]

    #
    # Extra sources currently uploading
    #
    pending_extra_sources = [ ]

    #
    # Deployment configuration
    #
    deployment_config = { }
    
    @staticmethod
    def get_queue():
        return manager.queue

    @staticmethod
    def register_client(client):
        blog.info("Adding client to manager '{}'.".format(client.get_identifier()))
        manager.client_array.append(client)
    
    @staticmethod
    def get_client(uuid):
        return manager.client_array[uuid]
    
    @staticmethod
    def get_client_by_name(name):
        for client in manager.client_array:
            if(client.get_identifier() == name):
                return client

        return None

    @staticmethod
    def remove_client(client):
        job = manager.get_job_by_client(client)

        if(job is not None):
            blog.warn("Build job '{}' aborted because the buildbot disconnected. Readding to head of queue..".format(job.get_jobid()))
            job.set_status("WAITING")
            manager.running_jobs.remove(job)
            manager.queued_jobs = [job] + manager.queued_jobs

        blog.info("Removing client '{}' from manager.".format(client.get_identifier()))
        manager.client_array.remove(client)

    @staticmethod
    def get_controller_clients():
        res = [ ]
        for cl in manager.client_array:
            if(cl.client_type == "CONTROLLER"):
                res.append(cl)
        return res

    @staticmethod
    def get_build_clients():
        res = [ ]
        for cl in manager.client_array:
            if(cl.client_type == "BUILD"):
                res.append(cl)
        return res
    
    @staticmethod
    def get_ready_build_clients():
        build_clients = manager.get_build_clients()
        res = [ ]
        for cl in build_clients:
            if(cl.is_ready):
                res.append(cl)
        return res

    @staticmethod
    def is_authkey_valid(authkey: str) -> bool:
        """
        Check if 'authkey' is a valid authkey..

        return: True if valid or untrusted mode, False if not
        """

        if(config.config.get_config_option("Masterserver")["UntrustedClients"] == "True"):
            return True

        # TODO: Will have to reimplement this part, once 
        # authkeys have permission levels
        authkey_line: str = config.config.get_config_option("Masterserver")["AuthKeys"]
        authkeys: list = config.config.parse_str_array(authkey_line)
        
        if(authkey in authkeys):
           return True
        else:
           return False

    # TODO: ------- job stuff should be moved to queue.py -------

    @staticmethod 
    def new_job(use_crosstools: bool, pkg_payload, requesting_client: str):
        job = Job(use_crosstools, pkg_payload, requesting_client)
        manager.queued_jobs.append(job)
        return job

    @staticmethod
    def add_job_to_queue(job):
        manager.queued_jobs.append(job)
    
    @staticmethod
    def move_inactive_job(job):
        manager.running_jobs.remove(job)
        manager.completed_jobs.append(job)

    @staticmethod 
    def get_job_by_client(client):
        for job in manager.running_jobs:
            if job in manager.running_jobs:
                if(job.buildbot == client):
                    return job

        return None
    
    @staticmethod
    def get_job_by_id(jid):
        for job in manager.running_jobs:
            if(job.job_id == jid):
                return job
        for job in manager.queued_jobs:
            if(job.job_id == jid):
                return job

        for job in manager.completed_jobs:
            if(job.job_id == jid):
                return job
        return None
    
    @staticmethod
    def get_queued_jobs():
        return manager.queued_jobs
    
    @staticmethod
    def get_running_jobs():
        return manager.running_jobs
    
    @staticmethod
    def get_completed_jobs():
        return manager.completed_jobs
    
    
    # TODO: -------------------------------------------------------

    @staticmethod
    def get_controller_names():
        res = [ ]

        for client in manager.client_array:
            if(client.client_type == "CONTROLLER"):
                res.append(client.get_identifier())

        return res

    @staticmethod
    def get_buildbot_names():
        res = [ ]

        for client in manager.client_array:
            if(client.client_type == "BUILD"):
                res.append(client.get_identifier())

        return res
    
    # TODO: ------- job stuff should be moved to queue.py -------

    @staticmethod
    def clear_completed_jobs():
        manager.completed_jobs = None
        manager.completed_jobs = [ ]
        manager.get_queue().update()

    @staticmethod 
    def cancel_queued_job(job):
        """
        Cancel a queued job.

        :param job: Job
        """
        if(not job in manager.queued_jobs):
            return False

        manager.queued_jobs.remove(job)
        manager.get_queue().update()
        return True

    @staticmethod
    def cancel_all_queued_jobs():
        manager.queued_jobs = [ ] 
    

    # TODO: -------------------------------------------------------
    
    @staticmethod
    def report_system_event(issuer, event):
        current_time = time.strftime("%H:%M:%S %d-%m-%Y", time.localtime())
        
        if(len(manager.system_events) > 50):
            manager.system_events.clear()
            manager.system_events.append("[{}] Branchmaster => Syslogs cleared.".format(current_time))

        manager.system_events.append("[{}] {} => {}".format(current_time, issuer, event))

    
    @staticmethod
    def get_pending_extra_sources():
        return manager.pending_extra_sources
    
    @staticmethod
    def add_pending_extra_source(pending_extra_src):
        manager.pending_extra_sources.append(pending_extra_src)

    @staticmethod
    def remove_pending_extra_source(pending_extra_src):
        manager.pending_extra_sources.remove(pending_extra_src)
    
    #
    # Determine deployment configuration. 
    #
    @staticmethod
    def determine_deployment_configuration():
        all_packages = packagebuild.package_build.parse_str_to_array(config.config.get_config_option("Deployment")["RealrootPackages"])
        can_provide_realroot = True

        for pkg in all_packages:
            if(not pkg in packagestorage.storage().get_packages_array()):
                can_provide_realroot = False
                break
        
        can_provide_crossroot = "crosstools" in packagestorage.storage().get_packages_array()
        
        try:
            server_url = config.config.get_config_option("Deployment")["CrosstoolsURL"]
            deploy_realroot = config.config.get_config_option("Deployment")["DeployRealroot"] == "True"
            deploy_crossroot = config.config.get_config_option("Deployment")["DeployCrosstools"] == "True"
        except KeyError:
            blog.error("Crosstools URLs missing in configuration file.")
            return False

        # Check if both are disabled.
        if(not deploy_realroot and not deploy_crossroot):
            blog.error("Crossroot and realroot disabled. Cannot continue.")
            return False
       
        #
        # Import crosstools package from upstream server
        #
        def import_crosstools_pkg(server_url):
            blog.info("Attempting to fetch crosstools package from specified URL..")
            
            blog.info("Attempting to fetch pkgbuild..")
            try:
                pkgbuild_str = requests.get(config.config.get_config_option("Deployment")["CrosstoolsPkgbuildURL"]).content.decode("utf-8")
            except KeyError:
                blog.error("Crosstools URLs missing in configuration file.")
                return False


            pkgb = packagebuild.package_build.from_string(pkgbuild_str)
            pkgbuildstorage.storage.add_packagebuild_obj(pkgb)

            blog.info("Pkgbuild imported. Fetching package..")

            try:
                with requests.get(server_url, stream=True) as r:
                    r.raise_for_status()
                    with open("crosstools.lfpkg", 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192): 
                            f.write(chunk)
            except Exception as ex:
                blog.error("Failed to fetch crosstools: {}".format(ex))
                return False

            blog.info("Fetched crosstools. Attempting to import..")
            stor = packagestorage.storage()
                    
            blog.info("Hashing package..")
            md5_hash = hashlib.md5()
            with open("crosstools.lfpkg", "rb") as hash_file:
                # read chunk by chunk
                for chunk in iter(lambda: hash_file.read(4096), b""):
                    md5_hash.update(chunk)

            blog.info("Deploying package to storage..")
            shutil.move("crosstools.lfpkg", stor.add_package(pkgb, md5_hash.hexdigest()))
            return True
        
        manager.deployment_config["deploy_realroot"] = can_provide_realroot and deploy_realroot

        # Check if crossroot is enabled, but not deployed.
        if(deploy_crossroot and not can_provide_crossroot):
            blog.warn("Crossroot enabled, but the package is unavailable.")
            
            # Can now provide crosstools
            if(import_crosstools_pkg(server_url)):
                can_provide_crossroot = True
            else:
                blog.error("Could not import crosstools.")
                return False

        manager.deployment_config["deploy_crossroot"] = can_provide_crossroot and deploy_crossroot

        #
        # Check if atleast one environment is available
        #
        if(deploy_realroot and not can_provide_realroot):
            blog.warn("Config requested realroot deployment, but the server cannot provide all required packages to install a realroot-environment.")

            # Attempt to fallback to crossroot, despite it being disabled, because its the only option.
            if(not deploy_crossroot):
                blog.warn("Attempting to fall back to crosstools, despite them being disabled.")

                if(can_provide_crossroot):
                    blog.warn("Crossroot is disabled in config, but is the only environment the server can provide.")
                    manager.deployment_config["deploy_crossroot"] = True
                    manager.report_system_event("Branchmaster", "Deployment configuration is invalid. Crosstools enabled, because it's the only environment the server can provide.")

                else:
                    blog.warn("Crossroot and realroot unavailable. Attempting to import crosstools from upstream..")
                    return import_crosstools_pkg(server_url)
        # config options
        manager.deployment_config["realroot_packages"] = all_packages
        manager.deployment_config["packagelisturl"] = config.config.get_config_option("Deployment")["HTTPPackageList"]

        manager.report_system_event("Branchmaster", "Deployment configuration reevaluated. Crosstools: {}, Realroot: {}".format(manager.deployment_config["deploy_crossroot"], manager.deployment_config["deploy_realroot"]))
        return True
