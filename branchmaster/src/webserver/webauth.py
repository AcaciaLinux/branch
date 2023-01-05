import time
import uuid

from log import blog
from webserver import usermanager


class web_auth():

    # static class wars
    # key - timestamp of last access
    authorized_keys = [ ]

    # user, hash pair
    user_hash = { }

    def __init__(self):
        blog.debug("Initializing web_auth object")

    
    #
    # clear out dead keys
    #
    def clear_dead_keys(self):
        blog.debug("Clearing dead keys..")
        curr_time = time.time()

        revoked_keys = 0

        for k in web_auth.authorized_keys:
            # key has expired
            if((curr_time - k.timestamp) > 900):
                web_auth.authorized_keys.remove(k)
                revoked_keys += 1
        
        blog.debug("Cleared {} dead keys.".format(revoked_keys))

    #
    # check if a user / phash pair match
    #
    def validate_pw(self, user, phash):
        bhash = phash.encode("utf-8")
        user_obj = usermanager.usermanager().get_user(user)
        
        if(user_obj is None):
            blog.debug("No such user.")
            return False

        return user_obj.validate_phash(phash) 


    #
    # returns a new key id, and authorizes the key object
    #
    def new_authorized_key(self):
        key_obj = key()

        blog.debug("Authorizing key '{}', timestamp: {}".format(key_obj.key_id, key_obj.timestamp))
        web_auth.authorized_keys.append(key_obj)
        return key_obj
   
    #
    # check if a given key is valid
    #
    def validate_key(self, key_id):
        blog.debug("Key validation requested.")
        
        self.clear_dead_keys()
        
        key_obj = None

        # does key exist
        for k in web_auth.authorized_keys:
            if(str(k.key_id) == key_id):
                key_obj = k
                break
        
        if(key_obj is None):
            blog.debug("Key validation failed. No such key found.")
            return False

        curr_time = time.time()

        # key has expired
        if((curr_time - key_obj.timestamp) > 900):
            blog.debug("Key validation failed. Key has expired.")
            self.invalidate_key(key_obj.key_id)
            return False
        
        # key is valid
        key_obj.timestamp = time.time()
        blog.debug("Key validation succeeded. Updating key timestamp: {}".format(key_obj.timestamp))
        return True

    def invalidate_key(self, key_id):
        blog.debug("Invalidating requested key")
        
        key_obj = None
        
        # does key exist
        for k in web_auth.authorized_keys:
            if(str(k.key_id) == key_id):
                key_obj = k
                break
        
        if(key_obj is None):
            blog.debug("Key validation failed. No such key found.")
            return False

        web_auth.authorized_keys.remove(key_obj)
        blog.debug("Key invalidated.")

class key():
    def __init__(self):
        self.key_id = uuid.uuid4();
        self.timestamp = time.time()

