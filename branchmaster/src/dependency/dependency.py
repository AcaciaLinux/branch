import blog
from localstorage import pkgbuildstorage
from manager import jobs
from manager import queue

#
# Gets all depender names
#
def find_dependers(pkgs, pkgname, visited):
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

#
# Create jobs from a solution
#
def job_arr_from_solution(manager, client, solution, use_crosstools):
    created_jobs = [ ]
    prev_jobs = [ ]

    for line in solution:
        new_prev_jobs = [ ]

        for pk in line:
            job = jobs.jobs(use_crosstools, True)
            job.pkg_payload = pkgbuildstorage.storage.get_packagebuild_obj(pk)
            
            if(job.pkg_payload is None):
                return None, pk

            job.requesting_client = client.get_identifier()
            
            for pj in prev_jobs:
                job.blocked_by.append(pj.job_id)

            job.set_status("WAITING")
            new_prev_jobs.append(job)
            created_jobs.append(job)
        
        prev_jobs = new_prev_jobs

    return created_jobs, ""

#
# Returns all the jobs contained in the queue that matches one of the names in deps_array
#
def package_dep_in_queue(in_queue: queue, deps_array):
    res = []

    for searchJob in in_queue:
        if (searchJob.pkg_payload.name in deps_array):
            res.append(searchJob)

    return res

#
# Updates every job in the queue and if it should be blocked by another one
#
def update_blockages(manager):
    blog.info("Recalculating blockages...")
    

    for job in manager.queued_jobs:

        # If the job is created by a solution submission
        # keep the explicitly defined blocking, but check if BLOCKED or WAITING
        if(job.solution_mode):
            blog.debug("Job is in solution mode. Keeping explicitly defined job-blocking.")
            job.set_status("WAITING")
    
            for blocker in job.blocked_by:
                if(any(queued_job.job_id == blocker for queued_job in manager.queued_jobs)):
                    blog.debug("Job '{}' ({}) is blocked by queued job defined in solution.".format(job.pkg_payload.name, job.job_id))
                    job.set_status("BLOCKED")
                    break
        
        # Check if the job should be blocked
        # by one of its dependencies.
        else:
            job.blocked_by = []

            # Select the correct dependency array
            if (job.use_crosstools):
                dependencies = job.pkg_payload.cross_dependencies
            else:
                dependencies = job.pkg_payload.build_dependencies

            # The queued jobs
            for job_found in package_dep_in_queue(manager.queued_jobs, dependencies):
                blog.debug("Job '{}' ({}) is blocked by queued job '{}' ({})".format(job.pkg_payload.name, job.job_id, job_found.pkg_payload.name, job_found.job_id))
                job.blocked_by.append(job_found.job_id)

            # The running jobs
            for job_found in package_dep_in_queue(manager.running_jobs, dependencies):
                blog.debug("Job '{}' ({}) is blocked by running job '{}' ({})".format(job.pkg_payload.name, job.job_id, job_found.pkg_payload.name, job_found.job_id))
                job.blocked_by.append(job_found.job_id)

            # Finished and "COMPLETED" jobs
            for job_found in package_dep_in_queue(manager.completed_jobs, dependencies):
                if (job_found.get_status() != "COMPLETED"):
                    blog.debug("Job '{}' ({}) is blocked by non-completed job '{}' ({}) [{}]".format(job.pkg_payload.name, job.job_id, job_found.pkg_payload.name, job_found.job_id, job_found.get_status()))
                    job.blocked_by.append(job_found.job_id)

            if (len(job.blocked_by) > 0):
                job.set_status("BLOCKED")
            else:
                job.set_status("WAITING")
