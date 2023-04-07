"""
Config module
"""
import os
import configparser
import blog

CONFIG_FILE = "/etc/branch/buildbot.conf"

class Config():
    """
    Config class based on configparser
    """
    config = configparser.ConfigParser()
    
    @staticmethod
    def setup():
        """
        Setup the config file
        """
        if (not os.path.exists(CONFIG_FILE)):
            Config.deploy_default_config()

        try:
            Config.config.read(CONFIG_FILE)
        except Exception as ex:
            blog.error(f"Could not parse configuration file: {ex}")
            return False

        return True

    @staticmethod
    def deploy_default_config():
        """
        Deploys the default configuration to CONFIG_FILE
        """

        # Deploys a default set of config options
        Config.config["Connection"] = {
            "ServerAddress": "127.0.0.1",
            "ServerPort": 27015,
            "AuthKey": "NONE",
            "Identifier": "a-branch-buildbot",
        }
        Config.config["Logger"] = {
            "EnableDebugLog": False
        }
        Config.config["BuildOptions"] = {
            "RealtimeBuildlog": False
        }

        with open(CONFIG_FILE, "w", encoding="utf8") as default_conf_file:
            Config.config.write(default_conf_file)

    @staticmethod
    def get_config():
        """
        Get ConfigParser object

        :return: ConfigParser object
        """
        return Config.config

    @staticmethod
    def get_config_option(option: str):
        """
        Get config option

        :param option: Option name as str
        """
        return Config.config[option]

    @staticmethod
    def parse_str_array(string: str) -> list:
        """
        Parse a list formatted as string to list
        "[a][b][c]" -> ["a", "b", "c"]

        :param string: The string to be parsed
        :return: List of strings
        """
        vals = []
        buff = ""

        for char in string:
            if (char == ']'):
                vals.append(buff)
                buff = ""
            elif (not char == '['):
                buff = buff + char

        return vals