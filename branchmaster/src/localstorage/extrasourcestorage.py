import os
import blog
import json
import packagebuild
import sqlite3
from threading import Lock

EXTRA_SOURCE_STORAGE_FILE="extrasources.db"

class extra_source_info():
    def __init__(self, _id, filename, description):
        self.id = _id
        self.filename = filename
        self.description = description
    
    def get_json(self):
        return {
                "id": self.id,
                "filename": self.filename,
                "description": self.description
        }

class storage():
    
    # only one thread can access an sqlite object at a time
    lock = Lock()
    
    @staticmethod
    def populate():
        blog.debug("Acquiring Database lock")
        
        try:
            db_connection = sqlite3.connect(EXTRA_SOURCE_STORAGE_FILE)
            storage.lock.acquire()
            cur = db_connection.cursor()

            res = cur.execute("SELECT name FROM sqlite_master")
            
            existing_tables = res.fetchone()
            if(existing_tables is None or "extrasources" not in existing_tables):
                blog.info("Creating table..")
                cur.execute("CREATE TABLE IF NOT EXISTS extrasources(id, filename, desc, extrasrc)")
                
            blog.debug("Releasing Database lock")
        except Exception as ex:
            blog.error("Could not populate database: {}".format(ex))

        storage.lock.release()
 

    @staticmethod
    def add_extrasource(_id, filename, desc, blob):
        blog.info("Inserting extra source to database: {} ({})".format(_id, desc))
        storage.lock.acquire()
        try:
            db_connection = sqlite3.connect(EXTRA_SOURCE_STORAGE_FILE)
            values = (_id, filename, desc, blob)

            # get a cursor
            cur = db_connection.cursor()
            cur.execute("INSERT INTO extrasources VALUES(?, ?, ?, ?)", values)
            db_connection.commit()
        except Exception as ex:
            blog.error("Could not insert to database: {}".format(ex))
            return False

        storage.lock.release()
        return True

    @staticmethod
    def get_all_extrasources():
        storage.lock.acquire()
        
       
        es_info = [ ]

        try:
            db_connection = sqlite3.connect(EXTRA_SOURCE_STORAGE_FILE)
            
            cur = db_connection.cursor()
            res = cur.execute("SELECT id, filename, desc FROM extrasources")

            for entry in res.fetchall():
                es_info.append(extra_source_info(entry[0], entry[1], entry[2]))

        except Exception as ex:
            blog.error("Could not get all extrasources from database: {}".format(ex))
    
        storage.lock.release()
        return es_info

    @staticmethod
    def get_extra_source_info_by_id(target_id):
        storage.lock.acquire()
        es_info = None

        try:
            db_connection = sqlite3.connect(EXTRA_SOURCE_STORAGE_FILE)
            
            cur = db_connection.cursor()
            res = cur.execute("SELECT id, filename, desc FROM extrasources WHERE id = '{}'".format(target_id)).fetchone()
            
            es_info = extra_source_info(res[0], res[1], res[2])

        except Exception as ex:
            blog.error("Could not get extrasource from database: {}".format(ex))
    
        storage.lock.release()
        return es_info


    @staticmethod
    def remove_extrasource_by_id(target_id):
        storage.lock.acquire()

        try:
            db_connection = sqlite3.connect(EXTRA_SOURCE_STORAGE_FILE)
            
            cur = db_connection.cursor()
            res = cur.execute("SELECT id FROM extrasources")

            # Delete extrasource if it exists
            for _id in res.fetchall():
                if(target_id == _id[0]):
                    cur.execute("DELETE FROM extrasources WHERE id='{}'".format(target_id))
                    blog.warn("Extrasource deleted: {}".format(target_id))
                    break

            db_connection.commit()

        except Exception as ex:
            blog.error("Could not delete extrasource: {}".format(ex))
    
        storage.lock.release()
    
    @staticmethod
    def get_extra_source_blob_by_id(target_id):
        storage.lock.acquire()
        blob = None

        try:
            db_connection = sqlite3.connect(EXTRA_SOURCE_STORAGE_FILE)
            cur = db_connection.cursor()
            res = cur.execute("SELECT extrasrc FROM extrasources WHERE id='{}'".format(target_id))
            blob = res.fetchone()

        except Exception as ex:
            blog.error("Could not get extrasource blob: {}".format(ex))
    
        storage.lock.release()
        return blob
