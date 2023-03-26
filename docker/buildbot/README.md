# Running this container:
```bash
docker run -v ./branchcfg:/etc/branch -v ./branchwd:/branchworkdirectory --privileged -it buildbot
```

This creates two directories in your current workdir: `branchcfg`(The config directory) and `branchwd`(The working directory).

