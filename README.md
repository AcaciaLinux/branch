# Branch - The AcaciaLinux packaging tool
'branch' is a simple to use tool written in python3 to create [leaf](https://github.com/AcaciaLinux/leaf) package files (.lfpkg) and run [BranchPackageBuilds](https://github.com/AcaciaLinux/BranchPackageBuilds).

# Usage: Packaging guide
A detailed packaging guide is available on the [wiki](https://github.com/AcaciaLinux/docs/wiki/Packaging).

# Usage: Branch package builds
The 'branch' package build system builds a package from a provided source using a special package.bpb file.

### File Layout: Example package (atk)
```txt
name=atk
version=2.38.0
source=https://download.gnome.org/sources/atk/2.38/atk-2.38.0.tar.xz
dependencies=[glib]
description=ATK provides the set of accessibility interfaces that are implemented by other toolkits and applications.
build={
	cd atk-2.38.0
	mkdir build &&
	cd    build &&

	meson --prefix=/usr --buildtype=release .. &&
	ninja
	
	DESTDIR=$PKG_INSTALL_DIR ninja install
}
```

### Creating a 'branch' package build file
A 'branch' package file can either be created manually or by using the provided utility:
```bash
branch bpbutil
```

### Available package builds
All package builds used in AcaciaLinux are available in the [Package build repository](https://github.com/AcaciaLinux/BranchPackageBuilds)

# Dependencies:
'branch' requires a python3 interpreter as well as [pysftp](https://pypi.org/project/pysftp/) and [requests](https://pypi.org/project/requests/). To install python dependencies run:

```bash
python3 -m pip install pysftp requests
```

# Installation:
'branch' can be installed on any distribution using the provided Makefile:
```bash
git clone https://github.com/AcaciaLinux/branch
cd branch
(sudo/doas) make install
```
A package file is available for AcaciaLinux, but it is likely out of date.

# Configuration
When launching 'branch' for the first time, it will run a configuration assistant to populate its configuration file located in ~/.config/branch/

```txt
>>> branch
Do you want to enable sftp support? (y/n)
y
Enter the Remote-Servers IP Address:
<HostName>
Enter remote username:
<remoteUser>
Enter the SSH-Key location:
<ssh_key>
WARNING: The SSH-Key passphrase is stored in plain text! (Enter for none)
Enter the SSH-Key passphrase:
<ssh_passphrase>
Enter sftp workdir: (Location where packages are stored on the Webserver)
<html_web_directory>
Enter web subdirectory: (https://xy.xy/SUBDIRECTORY/example-package)
<web_subdirectory>
Configuration completed.
```

To rerun this configuration assistant at any time, use:
```bash
branch reconf
```

### HostName
The address of the server the web- and SSH-server is running on. 

### remoteUser
User that has read/write access to <html_web_directory> for pushing the files onto the server

### ssh_key
SSH-key location on your local machine. By default it is located in ~/.ssh/id_rsa

### ssh_passphrase
In case your SSH-key has a passphrase, you can specify it here. ***WARNING*** The passphrase is stored in plaintext.

### web_subdirectory
The subdirectory used in the generated http url. Example: https://xy.xy/SUBDIRECTORY/example-package
