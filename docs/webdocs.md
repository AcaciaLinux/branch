## Branch webapi documentation

# WebResponse objects
The WebApi uses "WebResponse" objects to return a standarized response accross all api calls. The object is serialized in Json and contains the following fields:
- status
- response_code
- payload

# Sample response:
```
{
	"status": "SERV_FAILURE", 
	"response_code": 400,
	"payload": "Bad request."
}
```

# Api calls:
## HTTP-GET
- get
- / (root)
- test

## HTTP-POST
- auth
- checkauth
- logoff
- createuser
- crossbuild
- releasebuild
- viewlog
- clearcompletedjobs
- submitpackagebuild

# Missing data
All api endpoints return "MISSING_DATA" if a POST request field is missing and "AUTH_FAILURE" if the user is not authenticated.

# Endpoints:
## auth
Post-data: user / pass
Response:
- SUCCESS: Authkey as payload

## checkauth
Post-data: authkey
Response:
- SUCCESS: If authkey is valid.
- AUTH_FAILURE: If authkey is not valid.

## logoff
Post-data: authkey
Response:
- SUCCESS: 

## createuser
Post-data: authkey, cuser, cpass
Response:
- SERV_FAILURE: Invalid username
- SERV_FAILURE: User already exists 
- SUCCESS: User created

## crossbuild / releasebuild
Post-data: authkey, pkgname
Response:
- SUCESSS: Package build queued successfully
- SERV_FAILURE: No such package

## clearcompletedjobs
Post-data: authkey
Response:
- SUCCESS: jobs cleared

## submitpackagebuild
Post-data: authkey, packagebuild
Response:
- SUCCESS: packagebuild submission accepted.
- SERV_FAILURE: packagebuild is missing name, version or real_version

## viewlog 
Post-data: authkey, jobid
Response:
- SUCCESS: build_log as payload

## get
### leafpackagelist
Response: packagelist in plaintext

### packagelist
Response: packagelist as payload

### package
Get-data: ?pkgname=bla
Response: packagefile

### versions
Get-data: ?pkgname=bla
Response: list of versions in plain text

### packagebuildlist
Response: packagebuildlist as payload

### joblist
Response: joblist as payload

### packagebuild
Response: branch packagebuild as payload

### clientlist
Response: list of connected clients as payload

