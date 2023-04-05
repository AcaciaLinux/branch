CONFIG_FILE = "/etc/branch/master.conf"

import os
import blog
import configparser

class config():
    config = None

    @staticmethod
    def setup():
        if(not os.path.exists(CONFIG_FILE)):
            config.deploy_default_config()
        
        try:
            config.config = configparser.ConfigParser()
            config.config.read(CONFIG_FILE)
        except Exception as ex:
            blog.error("Could not parse configuration file: {}".format(ex))
            return -1

        return 0

    @staticmethod
    def deploy_default_config():
        config = configparser.ConfigParser()

        # Deploys a default set of config options
        config["Masterserver"] = {
            "ListenAddress": "0.0.0.0",
            "ServerPort": 27015,
            "AuthKeys": "[default]",
            "UntrustedClients": False,
        }
        config["HTTPServer"] = {
            "EnableWebServer": True,
            "HTTPPort": 8080,
            "UserFile": "/etc/branch/users.meta",
            "SendCorsHeaders": False,
            "KeyTimeout": 900
        }
        config["Logger"] = {
            "EnableDebugLog": False
        }
        config["Deployment"] = { 
            "CrosstoolsURL": "https://artifacts.acacialinux.org/cross-toolchain/crosstools.lfpkg",
            "CrosstoolsPkgbuildURL": "https://artifacts.acacialinux.org/cross-toolchain/crosstools.bpb",
            "RealrootPackages": "[base][glibc][gcc][make][bash][sed][grep][gawk][coreutils][binutils][findutils][automake][autoconf][file][gzip][libtool][m4][groff][patch][texinfo]",
            "DeployCrosstools": True,
            "DeployRealroot": True,
            "HTTPPackageList": "https://api.AcaciaLinux.org/?get=packagelist"
        }
        
        with open(CONFIG_FILE, "w") as default_conf_file:
            config.write(default_conf_file)

    @staticmethod
    def get_config():
        return config.config

    @staticmethod
    def get_config_option(option):
        return config.config[option]

    @staticmethod
    def parse_str_array(string):
        vals = [ ]
        buff = ""

        for c in string:
            if(c == ']'):
                vals.append(buff)
                buff = ""
            elif(not c == '['):
                buff = buff + c
    
        return vals
