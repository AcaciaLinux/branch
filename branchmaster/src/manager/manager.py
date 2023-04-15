import time
import blog
import requests
import hashlib
import shutil
import packagebuild

from localstorage import packagestorage
from localstorage import pkgbuildstorage
from config.config import Config
from manager.job import Job
from scheduler.branchqueue import BranchQueue
from scheduler.scheduler import BranchScheduler

class Manager():
    
    #
    # Static Objects
    #
    branch_queue = BranchQueue()
    branch_scheduler = BranchScheduler()

    #
    # Currently connected clients
    #
    client_array = [ ]
    
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
        return Manager.branch_queue
    
    @staticmethod
    def get_scheduler():
        return Manager.branch_scheduler

    @staticmethod
    def register_client(client):
        blog.info(f"Adding client to manager '{client.get_identifier()}' with type '{client.client_type}'.")
        Manager.client_array.append(client)
    
    @staticmethod
    def get_client(uuid):
        return Manager.client_array[uuid]
    
    @staticmethod
    def get_client_by_name(name):
        for client in Manager.client_array:
            if(client.get_identifier() == name):
                return client

        return None

    @staticmethod
    def remove_client(client):
        job = Manager.get_queue().get_running_job_by_client(client)

        if(job is not None):
            blog.warn("Build job '{}' aborted because the buildbot disconnected.".format(job.get_jobid()))
            Manager.get_queue().notify_job_aborted(job)
            
        blog.info("Removing client '{}' from manager.".format(client.get_identifier()))
        Manager.client_array.remove(client)

    @staticmethod
    def get_controller_clients():
        res = [ ]
        for cl in Manager.client_array:
            if(cl.client_type == "CONTROLLER"):
                res.append(cl)
        return res

    @staticmethod
    def get_build_clients():
        res = [ ]
        for cl in Manager.client_array:
            if(cl.client_type == "BUILD"):
                res.append(cl)
        return res
    
    @staticmethod
    def get_ready_build_clients() -> list:
        """
        Get all ready build clients

        :return list: Of Client objects
        """

        build_clients = Manager.get_build_clients()
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

        if(Config.get_config_option("Masterserver")["UntrustedClients"] == "True"):
            return True

        # TODO: Will have to reimplement this part, once 
        # authkeys have permission levels
        authkey_line: str = Config.get_config_option("Masterserver")["AuthKeys"]
        authkeys: list = Config.parse_str_array(authkey_line)
        
        if(authkey in authkeys):
           return True
        else:
           return False

    @staticmethod
    def get_controller_names():
        res = [ ]

        for client in Manager.client_array:
            if(client.client_type == "CONTROLLER"):
                res.append(client.get_identifier())

        return res

    @staticmethod
    def get_buildbot_names():
        res = [ ]

        for client in Manager.client_array:
            if(client.client_type == "BUILD"):
                res.append(client.get_identifier())

        return res
    
    @staticmethod
    def report_system_event(issuer, event):
        current_time = time.strftime("%H:%M:%S %d-%m-%Y", time.localtime())
        
        if(len(Manager.system_events) > 50):
            Manager.system_events.clear()
            Manager.system_events.append("[{}] Branchmaster => Syslogs cleared.".format(current_time))

        Manager.system_events.append("[{}] {} => {}".format(current_time, issuer, event))

    
    @staticmethod
    def get_pending_extra_sources():
        return Manager.pending_extra_sources
    
    @staticmethod
    def add_pending_extra_source(pending_extra_src):
        Manager.pending_extra_sources.append(pending_extra_src)

    @staticmethod
    def remove_pending_extra_source(pending_extra_src):
        Manager.pending_extra_sources.remove(pending_extra_src)
    
    #
    # Determine deployment configuration. 
    #
    @staticmethod
    def determine_deployment_configuration():
        all_packages = packagebuild.package_build.parse_str_to_array(Config.get_config_option("Deployment")["RealrootPackages"])
        can_provide_realroot = True

        for pkg in all_packages:
            if(not pkg in packagestorage.storage().get_packages_array()):
                can_provide_realroot = False
                break
        
        can_provide_crossroot = "crosstools" in packagestorage.storage().get_packages_array()
        
        try:
            server_url = Config.get_config_option("Deployment")["CrosstoolsURL"]
            deploy_realroot = Config.get_config_option("Deployment")["DeployRealroot"] == "True"
            deploy_crossroot = Config.get_config_option("Deployment")["DeployCrosstools"] == "True"
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
                pkgbuild_str = requests.get(Config.get_config_option("Deployment")["CrosstoolsPkgbuildURL"]).content.decode("utf-8")
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
        
        Manager.deployment_config["deploy_realroot"] = can_provide_realroot and deploy_realroot

        # Check if crossroot is enabled, but not deployed.
        if(deploy_crossroot and not can_provide_crossroot):
            blog.warn("Crossroot enabled, but the package is unavailable.")
            
            # Can now provide crosstools
            if(import_crosstools_pkg(server_url)):
                can_provide_crossroot = True
            else:
                blog.error("Could not import crosstools.")
                return False

        Manager.deployment_config["deploy_crossroot"] = can_provide_crossroot and deploy_crossroot

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
                    Manager.deployment_config["deploy_crossroot"] = True
                    Manager.report_system_event("Branchmaster", "Deployment configuration is invalid. Crosstools enabled, because it's the only environment the server can provide.")

                else:
                    blog.warn("Crossroot and realroot unavailable. Attempting to import crosstools from upstream..")
                    return import_crosstools_pkg(server_url)
        # config options
        Manager.deployment_config["realroot_packages"] = all_packages
        Manager.deployment_config["packagelisturl"] = Config.get_config_option("Deployment")["HTTPPackageList"]

        Manager.report_system_event("Branchmaster", "Deployment configuration reevaluated. Crosstools: {}, Realroot: {}".format(Manager.deployment_config["deploy_crossroot"], Manager.deployment_config["deploy_realroot"]))
        return True
