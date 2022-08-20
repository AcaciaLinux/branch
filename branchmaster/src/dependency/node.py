from dependency import dependency

class node():

    def __init__(self, name):
        self.name = name
        self.subnodes = [ ]
        self.blocked_by = ""

    def add_sub_node(self, node):
        self.subnodes.append(node)
    
    def get_sub_nodes(self):
        return self.subnodes

    def get_sobnode_by_name(self, nodename):
        for subnode in self.subnodes.subnodes:
            if(subnode.name == nodename):
                return subnode

    def print_tree(self):
        print(self.name, ":")

        for x in self.get_sub_nodes():
            print("==> ", x.name, " (blocked by:", x.blocked_by.name, ")")
            x.print_tree_tabbed(1)

    def print_tree_tabbed(self, tab):
        tabspace = "\t" * tab 
        tab = tab + 1

        for x in self.get_sub_nodes():
            print(tabspace, "==> ", x.name, " (blocked by:", x.blocked_by.name, ")")
            x.print_tree_tabbed(tab)
 
    def set_blockers(self):
        ##
        calc_blockers()

    def calc_blockers(self, jobs):
        for sub in self.get_sub_nodes():
            job = dependency.get_job_by_name(jobs, sub.name)
            job.blocked_by.append(dependency.get_job_by_name(jobs, sub.blocked_by.name).job_id)
            
            sub.calc_blockers(jobs)

    def get_deps_array(self):
        res = [ ]

        # add self aswell
        res.append(self.name)
        
        self.calc_deps_array(res)
        return res

    def calc_deps_array(self, res):

        for sub in self.get_sub_nodes():
            if(not sub.name in res):
                res.append(sub.name)
            sub.calc_deps_array(res)


