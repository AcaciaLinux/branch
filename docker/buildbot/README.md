# Running this container:
```bash
docker run -v ./branchcfg:/etc/branch -v ./branchwd:/branchworkdirectory --privileged -it buildbot
```

This creates two directories in your current workdir: `branchcfg`(The config directory) and `branchwd`(The working directory).

# Config
There are the following environment variables that get used:

```
BRANCH_SERVERURL - The url for the server
BRANCH_SERVERPORT - The port for the server
BRANCH_AUTHKEY - The authkey required
BRANCH_IDENTIFIER - The identifier to report to the masterserver
```

> **Note**
>
> These config options do only get applied if the config file does not exist!

