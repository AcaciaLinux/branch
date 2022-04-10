# Branch - The AcaciaLinux Packager
Branch is a really simple and efficient tool to prepare packages to be installed by [leaf](https://github.com/AcaciaLinux/leaf). Documentation on the packaging process ban be found in the [wiki article](https://github.com/AcaciaLinux/docs/wiki/Packaging).

# Installation
First, branch needs a dependency: `python3`. Install it by using your package manager, then we need to install `pysftp` using `pip` (which you may also install using your package manager). To do that, issue
```bash
python3 -m pip install pysftp
```
The next step is the installation by cloning the package, changing into it and issuing the installation command:
```bash
git clone https://github.com/AcaciaLinux/branch
cd branch
make install
```
**Note** that the last command `make install` may need superuser privileges, so you may execute it by putting `sudo` or `doas` before the command, depending on what you have installed.
# Configuration
The first time you start branch, it will ask you to go through a short configuration:
```txt
>>> branch
Do you want to enable sftp support? (y/n)
y
Enter the Remote-Servers IP Address:
<myHostName>
Enter remote username:
<remoteUser>
Enter the SSH-Key location:
<ssh_key>
WARNING: The SSH-Key passphrase is stored in plain text! (Enter for none)
Enter the SSH-Key passphrase:
<ssh_passphrase>
Enter sftp workdir: (Location where packages are stored on the Webserver)
<html_web_directory>
Enter web subdirectory: (https://xy.xy/SUBDIRECTORY/packages)
<web_subdirectory>
Configuration completed.
```
### myHostName
This is the hostname for the sftp and webserver you want to push your packages to

### remoteUser
The user that has write access to the <html_web_directory> for pushing the files onto the server

### ssh_key
The server should use ssh-access, so this is the location of the private key. Normally the default key generated with `ssh-keygen` is placed at `~/.ssh/id_rsa`.

### ssh_passphrase
SSH keys can be used in combination with a passphrase to provide more security. You may provide the passphrase for the key. ***WARNING*** The passphrase is exposed in branch's config and not encrypted!

### html_web_directory
The directory the webserver lives in. Should be `/var/www/html` when using the `apache` webserver.

### web_subdirectory
The directory from the hostname the packages live in. This should normally be `packages` on normal servers hosting leaf packages

## Note:
In order to make branch work with your remote server, you have to connect to it at least once via SSH by using the following command: `ssh <myHostName>`, responding with yes to the question if you want to add it to your known host. Then exit the shell using `exit`.
