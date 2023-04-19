#!python3

import sys

sys.path.append("/opt/branch/buildbot/src/config/")

from config import Config
Config.deploy_default_config()
