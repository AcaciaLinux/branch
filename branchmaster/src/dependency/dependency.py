import blog
from localstorage import pkgbuildstorage
from manager import job

# ------------------------------------------------
# TODO: this stuff should be moved to the scheduler and queue class

def find_dependers(pkgname, visited, use_crosstools):
    """
    Get all depender names
    """

    # get the appropriate dependencies for the build type
    cross_dependers = set()
    release_dependers = set()

    blog.debug(f"Calculating dependers for '{pkgname}'")
    pkg_dependers = pkgbuildstorage.storage.get_direct_dependers(pkgname, use_crosstools)
    
    if(use_crosstools):
        cross_dependers.add(pkgname)
    else:
        release_dependers.add(pkgname)
    
    visited.add(pkgname) 
    for dep in pkg_dependers:

        # we didnt resolve this package yet
        if dep not in visited:
            
            #visited.add(dep)
            # will use release deps
            if(len(pkgbuildstorage.storage.get_packagebuild_obj(dep).cross_dependencies) == 0):
                blog.info(f"Cross dependencies not set for {dep}")
                rd, cd = find_dependers(dep, visited, False)

            # will use cross deps
            else:
                blog.info(f"Cross dependencies set for {dep}")
                rd, cd = find_dependers(dep, visited, True)

            release_dependers.update(rd)
            cross_dependers.update(cd)

    return release_dependers, cross_dependers 


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
