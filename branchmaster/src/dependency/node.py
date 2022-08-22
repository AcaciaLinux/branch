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
    # Prints all subnode of current object
    #
    def print_tree(self):
        print(self.name, ":")

        for x in self.get_sub_nodes():
            print("==> ", x.name, " (blocked by:", x.blocked_by.name, ")")
            x.print_tree_tabbed(1)


    #
    # Prints all subnodes of current object, indented by 'tab'
    #
    def print_tree_tabbed(self, tab):
        tabspace = "\t" * tab 
        tab = tab + 1

        for x in self.get_sub_nodes():
            print(tabspace, "==> ", x.name, " (blocked by:", x.blocked_by.name, ")")
            x.print_tree_tabbed(tab)

    #
    # Calculate all blockers of 'jobs'
    #
    def calc_blockers(self, jobs):
        for sub in self.get_sub_nodes():
            job = dependency.get_job_by_name(jobs, sub.name)
            job.blocked_by.append(dependency.get_job_by_name(jobs, sub.blocked_by.name).job_id)
            
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


