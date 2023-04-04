#!python3
import requests
import sys
import random, string
from pathlib import Path

letters = string.ascii_letters
username = "".join(random.choice(letters) for i in range(15))
password = "".join(random.choice(letters) for i in range(15))
otherpass = "".join(random.choice(letters) for i in range(15))

if (len(sys.argv) != 3):
    print("Need the URL and root password for the API!")
    exit(-1)

api_url = sys.argv[1] + "/"
api_rootpw = sys.argv[2]
last_resp = []
user_authkey = ""
root_authkey = ""

OK = '\033[92m'
WARN = '\033[93m'
FAIL = '\033[91m'
ENDC = '\033[0m'

def ok():
    print("{}OK{}".format(OK, ENDC))

def fail():
    print("{}FAIL: {}{}".format(FAIL, last_resp["payload"], ENDC))

def p(text):
    print(text, end="", flush=True)

def pn(text):
    print(text)

def req(endpoint, data):
    global api_url
    global last_resp
    last_resp = requests.post(api_url + endpoint, data=data).json()
    return last_resp

def get(endpoint):
    global api_url
    return requests.get(api_url + "?get=" + endpoint).json()

# AUTH

p("Root login...")
if (req("auth", { "user": "root", "pass": api_rootpw })["response_code"] == 200):
    ok()
else:
    fail()
    pn("Will not continue!")
    exit(-1)

root_authkey = last_resp["payload"]

p("Logging in as wrong user...")
if (req("auth", { "user": username + "garbage", "pass": password})["response_code"] == 200):
    fail()
else:
    ok()

p("Logging in with wrong password...")
if (req("auth", { "user": username, "pass": password + "garbage"})["response_code"] == 200):
    fail()
else:
    ok()

# CHECKAUTH

p("Root checkauth ({})...".format(root_authkey))
if (req("checkauth", { "authkey": root_authkey })["response_code"] == 200):
    ok()
else:
    fail()

# CREATEUSER

p("Creating user...")
if (req("createuser", { "authkey": root_authkey, "cuser": username, "cpass": password})["response_code"] == 200):
    ok()
else:
    fail()

p("Logging in as user...")
if (req("auth", { "user": username, "pass": password})["response_code"] == 200):
    ok()
    user_authkey = last_resp["payload"]
else:
    fail()

p("User checkauth ({})...".format(user_authkey))
if (req("checkauth", { "authkey": user_authkey })["response_code"] == 200):
    ok()
else:
    fail()

p("Creating user as normal user (forbidden)...")
if (req("createuser", { "authkey": user_authkey, "user": username+"lgn", "pass": password })["response_code"] == 200):
    fail()
else:
    ok()

# CROSSBUILD

p("Submitting package build (crossbuild)...")
if (req("crossbuild", { "authkey": user_authkey, "pkgname": "crosstools" })["response_code"] == 200):
    ok()
else:
    fail()

p("Submitting package build as root (crossbuild)...")
if (req("crossbuild", { "authkey": root_authkey, "pkgname": "crosstools" })["response_code"] == 200):
    ok()
else:
    fail()

# RELEASEBUILD

p("Submitting package build (releasebuild)...")
if (req("releasebuild", { "authkey": user_authkey, "pkgname": "crosstools" })["response_code"] == 200):
    ok()
else:
    fail()

p("Submitting package build as root (releasebuild)...")
if (req("releasebuild", { "authkey": root_authkey, "pkgname": "crosstools" })["response_code"] == 200):
    ok()
else:
    fail()

# CLEARCOMPLETEDJOBS

p("Clearing completed jobs...")
if (req("clearcompletedjobs", { "authkey": root_authkey })["response_code"] == 200):
    ok()
else:
    fail()

p("Clearing completed jobs not authenticated (forbidden)...")
if (req("clearcompletedjobs", { "authkey": "" })["response_code"] == 200):
    fail()
else:
    ok()

# VIEWLOG

# SUBMITPACKAGEBUILD


txt = Path('testpkg').read_text()

p("Submit package build not authenticated (forbidden)...")
if (req("submitpackagebuild", { "authkey": "", "packagebuild": txt })["response_code"] == 200):
    fail()
else:
    ok()

p("Submit package build...")
if (req("submitpackagebuild", { "authkey": root_authkey, "packagebuild": txt })["response_code"] == 200):
    ok()
else:
    fail()

# CANCELQUEUEDJOB

p("Fetch job list...")
job_list = get("joblist")
if (job_list["response_code"] == 200):
    ok()
else:
    fail()

p("Cancel first queued job not authenticated (forbidden)...")
j_id = job_list["payload"]["queued_jobs"][0]["job_id"]
if (req("cancelqueuedjob", { "authkey": "", "jobid": j_id })["response_code"] == 200):
    fail()
else:
    ok()

p("Cancel first queued job...")
j_id = job_list["payload"]["queued_jobs"][0]["job_id"]
if (req("cancelqueuedjob", { "authkey": root_authkey, "jobid": j_id })["response_code"] == 200):
    ok()
else:
    fail()

# CANCELQUEUEDJOBS

p("Clearing queued jobs...")
if (req("cancelqueuedjobs", { "authkey": root_authkey })["response_code"] == 200):
    ok()
else:
    fail()

p("Clearing queued jobs not authenticated (forbidden)...")
if (req("cancelqueuedjobs", { "authkey": "" })["response_code"] == 200):
    fail()
else:
    ok()

# DELETEPACKAGE

p("Delete package not authenticated (forbidden)...")
if (req("deletepackage", { "authkey": "", "pkgname": "testing-package" })["response_code"] == 200):
    fail()
else:
    ok()

p("Delete package...")
if (req("deletepackage", { "authkey": root_authkey, "pkgname": "testing-package" })["response_code"] == 200):
    ok()
else:
    fail()

p("Delete package again...")
if (req("deletepackage", { "authkey": root_authkey, "pkgname": "testing-package" })["response_code"] == 200):
    fail()
else:
    ok()

# CLIENTINFO

p("Logoff...")
if (req("logoff", { "authkey": user_authkey })["response_code"] == 200):
    ok()
else:
    fail()

p("Checkauth after logoff...")
if (req("checkauth", { "authkey": user_authkey })["response_code"] == 200):
    fail()
else:
    ok()

p("Root Logoff...")
if (req("logoff", { "authkey": root_authkey })["response_code"] == 200):
    ok()
else:
    fail()

p("Root checkauth after logoff...")
if (req("checkauth", { "authkey": root_authkey })["response_code"] == 200):
    fail()
else:
    ok()
