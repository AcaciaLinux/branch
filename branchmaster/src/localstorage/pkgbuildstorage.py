import os
import blog
import json
import packagebuild
import sqlite3
from threading import Lock

class storage():
    
    # only one thread can access an sqlite object at a time
    lock = Lock()
    
    @staticmethod
    def populate():
        blog.debug("Acquiring Database lock")
        
        try:
            db_connection = sqlite3.connect("pkgbuild.db")
            storage.lock.acquire()
            cur = db_connection.cursor()

            res = cur.execute("SELECT name FROM sqlite_master")
            
            existing_tables = res.fetchone()
            if(existing_tables is None or "pkgbuilds" not in existing_tables):
                blog.info("Creating table..")
                cur.execute("CREATE TABLE IF NOT EXISTS pkgbuilds(name, real_version, version, source, extra_sources, description, dependencies, build_dependencies, cross_dependencies, buildscript)")
                
            blog.debug("Releasing Database lock")
        except Exception as ex:
            blog.error("Could not populate database: {}".format(ex))

        storage.lock.release()
       
    @staticmethod
    def get_packagebuild_obj(name):
        blog.debug("Acquiring Database lock")
        storage.lock.acquire()
        pkgbuild_obj = None
        try:
            db_connection = sqlite3.connect("pkgbuild.db")
            cur = db_connection.cursor()
            res = cur.execute("SELECT * FROM pkgbuilds WHERE name = ?", (name,))
            pkgbuild_result = res.fetchone()

            if(pkgbuild_result is None):
                storage.lock.release()
                return None
        
            pkgbuild_obj = packagebuild.package_build.from_list(pkgbuild_result)

            blog.debug("Releasing Database lock")
        except Exception as ex:
            blog.error("Could not get packagebuild from database: {}".format(ex))

        storage.lock.release()
        return pkgbuild_obj

    @staticmethod
    def add_packagebuild_obj(pkgbuild_obj):
        blog.info("Inserting pkgbuild to database: {}".format(pkgbuild_obj.name))
        storage.lock.acquire()
        try:
            db_connection = sqlite3.connect("pkgbuild.db")
            
            # remove packagebuild if it already exists
            cur = db_connection.cursor()
            res = cur.execute("DELETE FROM pkgbuilds WHERE name = ?", (pkgbuild_obj.name,))
            db_connection.commit()

            extra_sources = ""
            for item in pkgbuild_obj.extra_sources:
                extra_sources = "{}[{}]".format(extra_sources, item)

            dependencies = ""
            for item in pkgbuild_obj.dependencies:
                dependencies = "{}[{}]".format(dependencies, item)

            build_dependencies = ""
            for item in pkgbuild_obj.build_dependencies:
                build_dependencies = "{}[{}]".format(build_dependencies, item)

            cross_dependencies = ""
            for item in pkgbuild_obj.cross_dependencies:
                cross_dependencies = "{}[{}]".format(cross_dependencies, item)
            
            buildscript = ""
            
            if(pkgbuild_obj.build_script != [ ]):
                for i in range(0, len(pkgbuild_obj.build_script) - 1):
                    buildscript = "{}{}\n".format(buildscript, pkgbuild_obj.build_script[i])
                
                # last line does not have a newline
                buildscript = "{}{}".format(buildscript, pkgbuild_obj.build_script[len(pkgbuild_obj.build_script) - 1])

            values = (pkgbuild_obj.name, pkgbuild_obj.real_version, pkgbuild_obj.version, pkgbuild_obj.source, extra_sources, pkgbuild_obj.description,
                      dependencies, build_dependencies, cross_dependencies, buildscript)

            # get a cursor
            cur = db_connection.cursor()
            cur.execute("INSERT INTO pkgbuilds VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", values)
            db_connection.commit()
        except Exception as ex:
            blog.error("Could not insert to database: {}".format(ex))
            return False

        storage.lock.release()
        return True

    @staticmethod
    def get_all_packagebuilds():
        storage.lock.acquire()
        try:
            db_connection = sqlite3.connect("pkgbuild.db")
            
            # remove packagebuild if it already exists
            cur = db_connection.cursor()
            res = cur.execute("SELECT * FROM pkgbuilds")
            
            pkgbuilds = [ ]

            for match in res.fetchall():
                pkgbuild_obj = packagebuild.package_build.from_list(match)
                pkgbuilds.append(pkgbuild_obj)
        except Exception as ex:
            blog.error("Could not get all from database: {}".format(ex))

        storage.lock.release()
        return pkgbuilds

    @staticmethod
    def get_all_packagebuild_names():
        storage.lock.acquire()
        
        names = [ ]
        try:
            db_connection = sqlite3.connect("pkgbuild.db")
            
            # remove packagebuild if it already exists
            cur = db_connection.cursor()
            res = cur.execute("SELECT name FROM pkgbuilds")

            for r in res.fetchall():
                names.append(r[0])

        except Exception as ex:
            blog.error("Could not get all names from database.")
    
        storage.lock.release()
        return names

    @staticmethod
    def remove_packagebuild(pkg_name):
        storage.lock.acquire()

        try:
            db_connection = sqlite3.connect("pkgbuild.db")
            
            # remove packagebuild if it already exists
            cur = db_connection.cursor()
            res = cur.execute("SELECT name from pkgbuilds")
            
            # Delete packagebuild if it exists
            for name in res.fetchall():
                if(pkg_name == name[0]):
                    cur.execute("DELETE FROM pkgbuilds WHERE name='{}'".format(pkg_name))
                    blog.warn("Packagebuild deleted: {}".format(pkg_name))
                    break

            db_connection.commit()

        except Exception as ex:
            blog.error("Could not remove pkgbuild from database: {}".format(ex))


        storage.lock.release()
