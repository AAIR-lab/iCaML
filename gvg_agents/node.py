class Node:

    def __init__(self, state, parent, depth, action, action_cost):
        """
            Initializes the node data structure of the search tree.
            
            Parameters
            ===========
                state: State
                    The concrete state that this node represents.
                parent: State
                    The parent node of this node.
                depth: int
                    The depth of this node.
                action: Action
                    The action from the parent node's state that lead to this
                    node.
                action_cost: int
                    The cost of the specified action.
                    
            Returns
            ========
                None
        """
        self._state = state
        self._depth = depth
        self._parent = parent
        self._action = action
        self._action_cost = action_cost
        
        if self._parent is None:
        
            # If there is no parent then this node is the root node.
            self._total_action_cost = 0
        else:
        
            # Else, the path cost is the total cost of the actions of the
            # entire path.
            #
            # Note that the depth is also a path cost, however it ignores the
            # cost of the actions.
            self._total_action_cost = parent.get_total_action_cost() \
                + action_cost
        
    def get_state(self):
        """
            Returns
            ========
                State
                    The concrete state that this node represents.
        """
        return self._state
        
    def get_depth(self):
        """
            Returns
            ========
                int
                    The depth of this node assuming unit-cost actions.
        """
        return self._depth
        
    def get_parent(self):
        """
            Returns
            ========
                Node
                    The parent node of this node.
        """
        return self._parent
        
    def get_action(self):
        """
            Returns
            ========
                Action
                    The action from the parent node's concrete state that lead
                    to this node's concrete state.
        """
        return self._action
        
    def get_action_cost(self):
        """
            Returns
            ========
                int
                    The action cost of the action represented by this node.
        """
        return self._action_cost
        
    def get_total_action_cost(self):
        """
            Returns
            ========
                int
                    The total cost to this node accounting for different action
                    costs.
        """
        return self._total_action_cost
