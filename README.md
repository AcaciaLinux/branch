# Branch Package Build System
The AcaciaLinux package build and distribution system.

## Introduction
This repository contains a complete rewrite of the Branch package build system, featuring a client-server based architecture. The 'masterserver' accepts commands from 'controller' clients which can request 'release builds' (or to 'rebuild dependers') of a specified package build. The 'masterserver' relies on 'buildbots' to execute Branch package builds in a clean chroot environment, which then upload the created package file to the server.

The 'masterserver' also contains a webserver implementing a simple api to distribute package files.

## Package build distribution
The 'masterserver' is designed to handle multiple buildbots at the same time, to which requested package builds are submitted to. The server will queue package builds to every 'ready' buildbot, to effectively use available compute resources.

## Branch Package Builds
```
name=doas
version=6.8.1
real_version=0
source=https://github.com/Duncaen/OpenDoas/releases/download/v6.8.1/opendoas-6.8.1.tar.xz
dependencies=[linux-pam]
builddeps=[linux-pam]
description=Doas allows a normal user to gain root privileges
build={
	cd opendoas-6.8.1
	./configure --prefix=/usr --with-timestamp
	make -j$(nproc)
	make -j1 DESTDIR=$PKG_INSTALL_DIR install
}
```
Branch Package build files contain a build script and other necassary information. 

## Usage: masterserver
The masterserver can be configured in its configuration file located at `/etc/branch/master.conf`. By default, the server will listen for incoming client connections on port `27105` on `127.0.0.1`. The webserver will run on port `8080`.

## Usage: buildbot
The buildbot can be configured in its configuration file located at `/etc/branch/buildbot.conf`. The buildbot will setup it's base chroot install on first-run.

## Usage: client
The controller can be configured in its configuration file located at `/etc/branch/client.conf`. Use `branch -h` to list available commands.
