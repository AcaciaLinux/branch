import pysftp

print("Establishing connection..")
sftp_con = pysftp.Connection(host="84.252.121.236", username="root", private_key="~/.ssh/id_rsa", private_key_pass="")

print("Changing workdir")
sftp_con.cwd("/var/www/html/packages/")

print("Fetching pkglist")
sftp_con.get("leaf.pkglist")

print("Connection closed")
sftp_con.close()
