USER_FILE = "users.meta"

import json
import secrets
import os
import string
import bcrypt

from log import blog

#
# usermanager class
# 
class usermanager():
    
    users = [ ]
    initialized = False

    def __init__(self):
        blog.debug("Initializing user manager.")
        
        # clear
        usermanager.users = None
        usermanager.users = [ ]
    
        self.read_file()

    # fetches a user
    def get_user(self, uname):
        for u in usermanager.users:
            if(u.name == uname):
                return u

        return None

    # add a user
    def add_user(self, username, password):
        for u in usermanager.users:
            if(u.name == username):
                return False



        byte_array = password.encode('utf-8')
        salt = bcrypt.gensalt()
        phash = bcrypt.hashpw(byte_array, salt)

        user_obj = user(username, phash.decode("utf-8"))
        usermanager.users.append(user_obj)

        blog.debug("New user: updating file..")
        os.remove(USER_FILE)
        
        blog.debug("Writing updated file..")
        user_file = open(USER_FILE, "w")
        for u in usermanager.users:
            user_file.write("{}={}\n".format(u.name, u.phash))
       
        return True
        
    def read_file(self):
        blog.debug("Reading user file..")
        if(not os.path.exists(USER_FILE)):
            self.empty_config()


        user_file = open(USER_FILE, "r")
        user_file_arr = user_file.read().split("\n")

        for userl in user_file_arr:
            if(len(userl) == 0):
                continue
            
            # skip comments
            if(userl[0] == '#'):
                continue
            

            user_arr = userl.split("=")
            usern = user_arr[0]
            phash = user_arr[1]

            self.users.append(user(usern, phash))



    def empty_config(self):
        user_file = open(USER_FILE, "w")
        
        generator_chars = string.ascii_letters + string.digits + string.punctuation

        pwd = ""
        for i in range(16):
            pwd += "".join(secrets.choice(generator_chars))

        print()
        print()
        blog.warn("!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        blog.warn("NEW ROOT PASSWORD GENERATED!")
        blog.warn("!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        blog.warn("Password: {}".format(pwd))
        print()
        print()

        byte_array = pwd.encode('utf-8')
        salt = bcrypt.gensalt()
        phash = bcrypt.hashpw(byte_array, salt)

        user_file.write("root={}\n".format(phash.decode("utf-8")))
        user_file.close()

#
# user class
#
class user():
    
    # validate hash
    def validate_phash(self, chash):
        return bcrypt.checkpw(chash.encode("utf-8"), self.phash.encode("utf-8"))
        

    # init a user
    def __init__(self, name, phash):
        self.name = name
        self.phash = phash
