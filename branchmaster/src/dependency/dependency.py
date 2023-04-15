import blog
from localstorage import pkgbuildstorage
from manager import job

# ------------------------------------------------
# TODO: this stuff should be moved to the scheduler and queue class


def find_dependers(pkgs: list, pkgname: str, visited: set):
    """
    Get all depender names
    """
    release_build = [ ]
    cross_build = [ ]
    
    # iterate through all pkgbuilds.
    for pkg in pkgs:

        # if the package has cross_dependencies set, use cross deps
        if(pkg.cross_dependencies == [ ]):
            blog.debug("Cross dependency not set for {}, using build_dependencies.".format(pkg.name))

            if(pkgname in pkg.build_dependencies):
                if(pkg.name not in visited):
                    blog.debug("Adding package {} to releasebuilds".format(pkg.name))
                    visited.add(pkg.name)
                    release_build.append(pkg.name)

                    r,c = find_dependers(pkgs, pkg.name, visited) 
                    release_build.extend(r)
                else:
                    blog.error("Circular dependency. {} indirectly depends on itself!".format(pkg.name))

        # if the package has release dependecies set, use release deps
        else:
            blog.debug("Cross dependency set. Using cross_dependencies")
            if(pkgname in pkg.cross_dependencies):
                if(not pkg.name in visited):
                    blog.debug("Adding package {} to crossbuilds".format(pkg.name))
                    visited.add(pkg.name)
                    cross_build.append(pkg.name)

                    r,c = find_dependers(pkgs, pkg.name, visited)
                    cross_build.extend(c)
                else:
                    blog.warn("Circular dependency. {} indirectly depends on itself!".format(pkg.name))
    
    return release_build, cross_build

def job_arr_from_solution(client, solution, use_crosstools):
    """
    Job array from provided solution
    
    :param client: The requesting client
    :param solution: The provided solution
    :param use_crosstools: Build solution in crosstools mode
    """
    created_jobs = [ ]
    prev_jobs = [ ]

    for line in solution:
        new_prev_jobs = [ ]

        for pk in line:
            job_obj = job.Job(use_crosstools, pkgbuildstorage.storage.get_packagebuild_obj(pk), client.get_identifier(), True)
            
            # invalid solution, since we couldn't find one of the packages
            if(job_obj.pkg_payload is None):
                return None, pk
            
            # find blocked by
            for pj in prev_jobs:
                job_obj.blocked_by.append(pj.id)

            new_prev_jobs.append(job_obj)
            created_jobs.append(job_obj)
        
        prev_jobs = new_prev_jobs

    return created_jobs, ""

def package_dep_in_queue(in_queue, deps_array):
    """
    Return all jobs from the given queue
    that match on of the names in deps_array

    :param deps_array: List of dependencies
    :in_queue: List object
    """
    res = []

    for searchJob in in_queue:
        if (searchJob.pkg_payload.name in deps_array):
            res.append(searchJob)

    return res