class node():

    def __init__(self, name):
        self.name = name
        self.subnodes = [ ]

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
            print("==>", x.name)
            x.print_tree_tabbed(1)

    def print_tree_tabbed(self, tab):
        tabspace = "\t" * tab 
        tab = tab + 1

        for x in self.get_sub_nodes():
            print(tabspace, "==>", x.name)
            x.print_tree_tabbed(tab)



