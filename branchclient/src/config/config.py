CONFIG_FILE = "/etc/branch/client.conf"

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
        config["Connection"] = {
            "ServerAddress": "127.0.0.1",
            "ServerPort": 27015,
            "AuthKey": "NONE",
            "Identifier": "a-branch-client",
        }
        config["Logger"] = {
            "EnableDebugLog": False
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
