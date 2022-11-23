import os

from config import config

HEADER = '\033[95m'
NORMAL = '\033[94m'
OKCYAN = '\033[96m'
OKGREEN = '\033[92m'
WARNING = '\033[93m'
FAIL = '\033[91m'
ENDC = '\033[0m'
BOLD = '\033[1m'
UNDERLINE = '\033[4m'

# used to determine if logger is running inside docker
NO_TERM = True

def initialize():
    if("TERM" in os.environ):
        global NO_TERM
        NO_TERM = False
    else:
        print("No terminal available. Disabling log color.")
    
def warn(log):
    global NO_TERM

    if(NO_TERM):
        print("==> [WARN] " + log)
    else:
        print(WARNING + "==> [WARN] " + ENDC + log)

def error(log):
    global NO_TERM
    
    if(NO_TERM):
        print("==> [ERROR] " + log)
    else:
        print(FAIL + "==> [ERROR] " + ENDC + log)

def info(log):
    global NO_TERM

    if(NO_TERM):
        print("==> " + log)
    else:
        print(OKGREEN + "==> " + ENDC + log)

def web_log(log):
    global NO_TERM 

    if(NO_TERM):
        print(" -> " + log)
    else:
        print(OKCYAN + " -> " + ENDC + log)

def debug(log):
    global NO_TERM

    if(config.branch_options.debuglog):
        if(NO_TERM):
            print("==> [DEBUG] " + log)
        else:
            print(OKGREEN + "==> [DEBUG] " + ENDC + log)
