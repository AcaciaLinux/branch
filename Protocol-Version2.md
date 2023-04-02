# Branch Protocol V2 specification
New version of the branch protocol. "BYTE_LENGTH" refers to length 
in bytes of the actual request string. 

## Versioning
A version check is implemented in the authentication command. 
Only clients on the same version can connect to the server, 
to ensure the api being compatible. No attempt to be backwards compatible is made.
Clients on an older or newer version are rejected.

- 0:  Initial implementation
- 1:  ..
- 2:  ..

## Status Codes
- 100 -> (UNUSED)
- 200 -> OK
- 300 -> (UNUSED)
- 400 -> REQUEST_FAILURE
- 500 -> INTERNAL_SERVER_ERROR
- 600 -> (UNUSED)

## Request 
```json
BYTE_LENGTH {
	command: "",
	payload: ""
}
```

## Response
```json
BYTE_LENGTH {
	statuscode: 200,
	payload: ""
}
```
<br>
<br>

# Authentication Command
### Request
```json
BYTE_LEN {
	"command": "AUTH",
	"payload": {
		"machine_identifier": "username",
		"machine_type": "CONTROLLER",
		"machine_authkey": "authkey" || "",
		"machine_version": PROTO_VERSION
	}
}
```

### Response
```json
BYTE_LENGTH {
	"statuscode": 200 || 400 || 500,
	"payload": {
		"auth_status": "DESCRIPTION"
		"logon_message": "Short server status message..? Errors encountered.."
	} || "Logon failure message"
}

```
After successful authentication the client is allowed to execute either [Controller Commands]() or [Buildbot Commands]().
<br>
<br>

# Controller Commands
## Checkout
### Request
```json
BYTE_LEN {
	"command": "CHECKOUT",
	"payload": "PACKAGE_NAME"
}
```

### Response
```json
BYTE_LENGTH {
	statuscode: 200 || 400 || 500,
	payload: "ERROR MSG" || pkgbuild
}
```
<br>
<br>

## Submit
### Request
```json
BYTE_LEN {
	"command": "SUBMIT",
	"payload": pkgbuild
}
```

### Response
```json
BYTE_LENGTH {
	statuscode: 200 || 400 || 500,
	payload: "DESCRIPTION"
}
```
<br>
<br>

## Releasebuild / Crossbuild

### Request
```json
BYTE_LEN {
	"command": "BUILD",
	"payload": { 
		"pkgname": "PKG_NAME",
		"buildtype": "CROSS" || "RELEASE"
}
```

### Response
```json
BYTE_LENGTH {
	statuscode: 200 || 400 || 500,
	payload: "DESCRIPTION"
}
```
<br>
<br>

## View job log
### Request
```json
BYTE_LEN {
	"command": "GETJOBLOG",
	"payload": "JOBID"
}
```
### Response
```json
BYTE_LEN {
	statuscode: 200 || 400 || 500,
	"payload": [ "Line1", "Line2", "Line3" ] || "No such job id"
}
```
<br>
<br>

## View sys log
### Request
```json
BYTE_LEN {
	"command": "GETSYSLOG",
	"payload": ""
}
```
### Response
```json
BYTE_LEN {
	statuscode: 200 || 500,
	"payload": [ "Syslog-line", "Syslog-line2", "Syslog-line3" ]
}
```
<br>
<br>

## Get package dependers
### Request
```json
BYTE_LEN {
	"command": "GETDEPENDERS",
	"payload": "PKG_NAME"
}
```
### Response
```json
BYTE_LEN {
	statuscode: 200 || 400 || 500,
	"payload": {
		"releasebuild": ["package1", "package2", "package3"],
		"crossbuild": ["package4", "package5" ]
	}
}
```
<br>
<br>

## Rebuild package dependers
### Request
```json
BYTE_LEN {
	"command": "REBUILDDEPENDERS",
	"payload": "PKG_NAME"
}
```
### Response
```json
BYTE_LEN {
	statuscode: 200 || 400 || 500,
	"payload": "DESCRIPTION"
}
```
<br>
<br>

## Get job status
### Request
```json
BYTE_LEN {
	"command": "GETJOBSTATUS",
	"payload": ""
}
```
### Response
```json
BYTE_LEN {
	statuscode: 200 || 500,
	"payload": {
		"queuedjobs": [ .. ],
		"runningjobs": [ { job_id: "uuid", job_status: "STATUS", job_name: "NAME", requesting_client: "CLIENT_NAME" }, { .. } , { .. } ],
		"completedjobs": [ .. ],
	}
}
```
<br>
<br>

## Get connected clients
### Request
```json
BYTE_LEN {
	"command": "GETCONNECTEDCLIENTS",
	"payload": ""
}
```
### Response
```json
BYTE_LEN {
	statuscode: 200 || 500,
	"payload": {
		"controllers": [ "client1", "client2", "client3" ],
		"buildbots": [ "client4", "client5", "client6" ]
	}
}
```
<br>
<br>

## Get managed packages
### Request
```json
BYTE_LEN {
	"command": "GETMANAGEDPKGS",
	"payload": ""
}
```
### Response
```json
BYTE_LEN {
	statuscode: 200 || 500,
	"payload": [ "package1", "package2", "package3" ],
}
```
<br>
<br>

## Get managed packagebuilds
### Request
```json
BYTE_LEN {
	"command": "GETMANAGEDPKGBUILDS",
	"payload": ""
}
```
### Response
```json
BYTE_LEN {
	statuscode: 200 || 500,
	"payload": [ "packagebuild1", "packagebuild2", "packagebuild3" ],
}
```

<br>
<br>

## Clear completed jobs
### Request
```json
BYTE_LEN {
	"command": "CLEARCOMPLETEDJOBS",
	"payload": ""
}
```
### Response
```json
BYTE_LEN {
	statuscode: 200 || 500,
	"payload": "Description",
}
```

<br>
<br>

## Cancel all queued jobs
### Request
```json
BYTE_LEN {
	"command": "CANCELQUEUEDJOBS",
	"payload": ""
}
```
### Response
```json
BYTE_LEN {
	statuscode: 200 || 500,
	"payload": "Description",
}
```

<br>
<br>

## Cancel a queued job by id
### Request
```json
BYTE_LEN {
	"command": "CANCELQUEUEDJOB",
	"payload": "job_id"
}
```
### Response
```json
BYTE_LEN {
	statuscode: 200 || 400 || 500,
	"payload": "Description",
}
```

<br>
<br>

## Submit a solution file for building
### Request
```json
BYTE_LEN {
	"command": "SUBMITSOLUTION",
	"payload": {
		"solution": [ [ "step1" ], [ "step2-1", "step2-2", "step2-3" ], [ "step3" ] ],
		"buildtype": "CROSS" || "RELEASE"
	}
}
```
### Response
```json
BYTE_LEN {
	statuscode: 200 || 400 || 500,
	"payload": "Description"
}
```

<br>
<br>

## Get a clients available information
### Request
```json
BYTE_LEN {
	"command": "GETCLIENTINFO",
	"payload": ""
}
```
### Response
```json
BYTE_LEN {
	statuscode: 200 || 400 || 500,
	"payload": {
		"Connection Timestamp": 0,
		...
	}
}
```

<br>
<br>

## Delete tracked package and packagebuild
### Request
```json
BYTE_LEN {
	"command": "DELETEPKG",
	"payload": "pkgname"
}
```
### Response
```json
BYTE_LEN {
	statuscode: 200 || 400 || 500,
	"payload": "DESCRIPTION"
}
```

<br>
<br>

## Get list of extra sources
### Request
```json
BYTE_LEN {
	"command": "GETMANAGEDEXTRASOURCES",
	"payload": ""
}
```
### Response
```json
BYTE_LEN {
	statuscode: 200 || 400 || 500,
	"payload": [
		{ id: "aa-aa", filename: "filename.txt", description: "A test file" },
		...
	]
}
```

<br>
<br>

## Remove extra sources
### Request
```json
BYTE_LEN {
	"command": "REMOVEEXTRASOURCE",
	"payload": "es-id"
}
```
### Response
```json
BYTE_LEN {
	statuscode: 200 || 400 || 500,
	"payload": "Description"
}
```

<br>
<br>

## Transfer extra sources
### Request
```json
BYTE_LEN {
	"command": "TRANSFEREXTRASOURCE",
	"payload": {
		"filename": "filename.txt"
		"filedescription": "A plaintext description"
		"filelength": 6000 (BYTES)
	}
}
```
### Response
```json
BYTE_LEN {
	statuscode: 200 || 400 || 500,
	"payload": "Mode switched." || "Failure description message"
}
```
After setting up file transfer, send extrasource file using the same socket. The server 
will send an acknowledge once the server has received all bytes.
### Response 2
```json
BYTE_LEN {
	statuscode: 200 || 400 || 500,
	"payload": "File transfer complete" || "Failure description message"
}
```

<br>
<br>

## Complete extra source transfer
### Request
```json
BYTE_LEN {
	"command": "COMPLETETRANSFER",
	"payload": ""
}
```
### Response
```json
BYTE_LEN {
	statuscode: 200 || 400 || 500,
	"payload": "Transfer complete." || "Failure description message"
}
```

<br>
<br>

# Notes:
- (?) Remove COMPLETETRANSFER and add it to the callback Response 2
- remove GET_LOCKED_PACKAGES, as it isn't very useful.

# Buildbot Commands
## TODO: Once implementation is further along, should be straight forward.

