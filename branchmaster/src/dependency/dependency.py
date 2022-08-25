from log import blog
from localstorage import pkgbuildstorage
from dependency import node
from manager import jobs

#
# Get all dependencies in a list
#
def get_all_deps(pkg_name):
    storage = pkgbuildstorage.storage()
    
    calculated = [ ]
    deps = [ ]
    res  = calculate_list(storage, pkg_name, calculated, deps)
    return res

#
# Calculates a dependency tree and return its masternode object 
#
def get_dependency_tree(pkg_name):
    storage = pkgbuildstorage.storage()

    masternode = node.node(pkg_name)
    calculated = [ ]

    res = calculate_tree(storage, calculated, masternode)  
    return masternode

#
# Returns a full depender tree
#
def calculate_tree(storage, calculated, masternode):
    # Ignore circular dependencies
    if(masternode.name in calculated):
        blog.debug("Circular dependency ignored.")
        return None
   
    # Add self to already calculated packages.
    calculated.append(masternode.name)
    blog.debug("Finding dependers for {}...".format(masternode.name))

    for pkg in storage.packages:
        pkg_build = storage.get_bpb_obj(pkg)
        
        if(masternode.name in pkg_build.dependencies or masternode.name in pkg_build.dependencies):
            blog.debug("Adding to dependers.. {}".format(pkg))
            
            # Add sub node
            newnode = node.node(pkg)
            newnode.blocked_by = masternode
            masternode.add_sub_node(newnode)
            
            # calculate dependencies for subnodes
            calculate_tree(storage, calculated, newnode)
            continue

#
# Returns dependers as list
#
def calculate_list(storage, pkg_name, calculated, deps):
    if(pkg_name in calculated):
        blog.debug("Already calculated {}! Skipping calculation..".format(pkg_name))
        return
    
    ldeps = [ ]

    blog.debug("Finding dependers (one level deep) for {}...".format(pkg_name))

    for check_pkg in storage.packages:
        pkg_build = storage.get_bpb_obj(check_pkg)
        
        if(pkg_name in pkg_build.dependencies):
            if(not check_pkg in deps):
                blog.debug("Adding to dependers.. {}".format(check_pkg))
                deps.append(check_pkg)
                ldeps.append(check_pkg)
            else:
                blog.debug("Already in dependers.. {}".format(check_pkg))

            continue

        if(pkg_name in pkg_build.build_dependencies):
            if(not check_pkg in deps):
                blog.debug("Adding to dependers.. {}".format(check_pkg))
                deps.append(check_pkg)
                ldeps.append(check_pkg)
            else:
                blog.debug("Already in dependers.. {}".format(check_pkg))

            continue

    calculated.append(pkg_name)

    for pkg in ldeps:
        calculate_list(storage, pkg, calculated, deps)
        
    return deps

#
# Get job array
#
def get_job_array(manager, client, dependencies):
    job_array = [ ]
    stor = pkgbuildstorage.storage()
    
    if(dependencies is None):
        return None

    for dependency in dependencies:
        job = manager.new_job()
        job.build_pkg_name = dependency
        job.pkg_payload = stor.get_bpb_obj(dependency)
        
        job.requesting_client = client.get_identifier()

        job.set_status("JOB_WAITING")
        job_array.append(job)

    return job_array

#
# Find a job by name in a jobs array
#
def get_job_by_name(jobs, name):
    for job in jobs:
        if(job.build_pkg_name == name):
            return job

#
# Find a job by job id in a jobs array
#
def get_job_by_id(jobs, jid):
    for job in jobs:
        if(job.job_id == jid):
            return job

