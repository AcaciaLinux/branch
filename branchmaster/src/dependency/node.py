import blog

from dependency import dependency

class node():

    def __init__(self, name):
        self.name = name
        self.subnodes = [ ]
        self.blocked_by = ""

    #
    # Adds a subnode to the current node
    #
    def add_sub_node(self, node):
        self.subnodes.append(node)
    
    #
    # Get subnodes from current node
    #
    def get_sub_nodes(self):
        return self.subnodes

    #
    # Get subnode by name 
    #
    def get_sobnode_by_name(self, nodename):
        for subnode in self.subnodes.subnodes:
            if(subnode.name == nodename):
                return subnode

    #
    # Fetches subnode of current object
    #
    def get_tree_str(self):
        result = ""
        result = result + "{} -> ({}):\n".format(self.name, self.blocked_by)

        for x in self.get_sub_nodes():
            result = result + "-> {} (blocked by: {})\n".format(x.name, x.blocked_by.name)
            result = result + x.get_tree_tabbed(1)

        return result
    

    #
    # Fetches all subnodes of current object, indented by ' '
    #
    def get_tree_tabbed(self, tab):
        tabspace = "\t" * tab 
        tab = tab + 1
        
        result = ""

        for x in self.get_sub_nodes():
            result = result + "{}-> {} (blocked by: {})\n".format(tabspace, x.name, x.blocked_by.name)
            result = result + x.get_tree_tabbed(tab)
        
        return result
        
    #
    # Calculate all blockers of 'jobs'
    #
    def calc_blockers(self, jobs):
        blog.debug("Calculating blockers for: {}".format(self.name))
        for sub in self.get_sub_nodes():
            job = dependency.get_job_by_name(jobs, sub.name)
            job.blocked_by.append(dependency.get_job_by_name(jobs, sub.blocked_by.name).job_id) 
            
            blog.debug("Job {} blocked by: {}".format(self.name, job.blocked_by))

            if(job.blocked_by == [ ]):
                job.set_status("WAITING")
            else:
                job.set_status("BLOCKED")

            sub.calc_blockers(jobs)

    #
    # Gets an array of all dependencies
    #
    def get_deps_array(self):
        res = [ ]

        # add self
        res.append(self.name)
        
        self.calc_deps_array(res)
        return res

    #
    # Calculate dependency array
    #
    def calc_deps_array(self, res):
        # recurse through all subnodes and add calc_deps_array
        for sub in self.get_sub_nodes():
            if(not sub.name in res):
                res.append(sub.name)
            sub.calc_deps_array(res)


