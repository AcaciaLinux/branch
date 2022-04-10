# Branch - The AcaciaLinux packaging tool
'branch' is a simple tool written in python3 to create [leaf](https://github.com/AcaciaLinux/leaf) package files (.lfpkg)

# Usage: Packaging guide
A detailed packaging guide is available on the [wiki](https://github.com/AcaciaLinux/docs/wiki/Packaging).

# Dependencies:
'branch' requires a python3 interpreter as well as [pysftp](https://pypi.org/project/pysftp/). pysftp can be installed with the python pip package manager:

```bash
python3 -m pip install pysftp
```

# Installation:
'branch' can be installed using the provided Makefile:

```bash
git clone https://github.com/AcaciaLinux/branch
cd branch
make install
```

Todo: lfpkg for branch

# Configuration
When launching 'branch' for the first time, it will run a configuration assistant to populate its configuration file located at ~/.config/branch/branch.conf

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
