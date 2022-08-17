from log import blog
from localstorage import localstorage
from dependency import node


# dependers -> packages that need this package
# dependeny -> packages that this package needs

def get_all_deps(pkg_name):
    storage = localstorage.storage()
    
    calculated = [ ]
    deps = [ ]
    res  = calc_sarray(storage, pkg_name, calculated, deps)
    return res


def get_node_tree(pkg_name):
    storage = localstorage.storage()

    masternode = node.node(pkg_name)

    calculated = [ ]
    deps = [ ]
    res = calc(storage, pkg_name, calculated, deps, masternode)
    
    masternode.print_tree()


def calc(storage, pkg_name, calculated, deps, masternode):
    if(pkg_name in calculated):
        blog.debug("Already calculated {}! Skipping calculation..".format(pkg_name))
        return None
    
    
    ldeps = [ ]
    blog.debug("Finding dependers (one level deep) for {}...".format(pkg_name))

    for check_pkg in storage.packages:
        pkg_build = storage.get_bpb_obj(check_pkg)
        
        if(pkg_name in pkg_build.dependencies):
            if(not check_pkg in deps):
                blog.info("Adding to dependers.. {}".format(check_pkg))
                
                deps.append(check_pkg)
                ldeps.append(check_pkg)
            else:
                blog.info("Already in dependers.. {}".format(check_pkg))

            continue

        if(pkg_name in pkg_build.build_dependencies):
            if(not check_pkg in deps):
                blog.info("Adding to dependers.. {}".format(check_pkg))
                ldeps.append(check_pkg)
                deps.append(check_pkg)
            else:
                blog.info("Already in dependers.. {}".format(check_pkg))

            continue

    calculated.append(pkg_name)
    
    for pkg in ldeps:

        print("=======================================")
        print("CURRENT MASTER: {}".format(masternode.name))



        print("ADDING SUB {} TO MASTER: {}".format(pkg, masternode.name))
        nnode = node.node(pkg)
        masternode.add_sub_node(nnode)
   
        #masternode.print_tree()

        print("CALCULATING SUBS FOR {}".format(nnode.name))
        print("calc: pkg: {} name: {}".format(pkg, nnode.name))
        print("=======================================")
        if(calc(storage, pkg, calculated, deps, nnode) is None):
            print("SKIPPED DEPS FOR {}".format(pkg))
            print("=======================================")

    #for pkg in ldeps:
    #    print("calling calc for"
    #
    #    nnode = node.node(pkg)
    #    
    #    calc(storage, pkg, calculated, deps, nnode)
    return deps

#
# Returns dependers in unordered list
#
def calc_sarray(storage, pkg_name, calculated, deps):
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
        calc_sarray(storage, pkg, calculated, deps)
        
    return deps
