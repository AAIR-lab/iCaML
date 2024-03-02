import heapq
import itertools

class PriorityQueue:
    """
        A class that implements the Priority Queue for search algorithms.
        
        This priority queue is a min-priority queue.
    """
    
    # This marker allows us to update priorities of duplicate entries without
    # incurring a O(logn) cost.
    _REMOVED_TOKEN = 0xDEADC0DE

    def __init__(self):
        """
            Initializes this priority queue.
        """
        
        # The priority queue data structure.
        self._pq = []
        self._size = 0
        
        # We use a simple tie breaker that just increments a counter by 1 each
        # time an entry is added. So, for two items having equal priorities,
        # the one which came earlier is popped first.
        self._tie_breaker = itertools.count()
        
        # We store the state -> node map so that if we are pushing a node with
        # the same state, we can update the priority while invalidating the
        # other entry.
        self._state_dict = {}

    def push(self, priority, node):
        """
            Pushes a node into the priority queue.
            
            Parameters
            ===========
                priority: int
                    The priority of the entry.
                node: Node
                    The node to be pushed.
        """
        
        state = node.get_state()
        
        # Initialize the new entry.
        old_entry = None
        new_entry = [priority, next(self._tie_breaker), node, state]

        # If the state is already the priority queue, then we might
        # need to update the priority of the state.
        if state in self._state_dict:

            # Get the old entry.
            old_entry = self._state_dict[state]
            
            # If the old entry has a lower value (greater priority) then we
            # mark it as invalid.
            if old_entry[0] > priority:
                
                old_entry[-1] = PriorityQueue._REMOVED_TOKEN
            else:
                
                # Else, simply set the old entry as the new entry.
                # We do not need to push to the priority queue in this case.
                #
                # Note that we shouldn't get here for algorithms like A* but
                # we might get here for other algorithms.
                new_entry = old_entry

        # Store the entry and push to the queue (if needed).
        self._state_dict[state] = new_entry
        if old_entry is not new_entry:
    
            self._size += 1
            heapq.heappush(self._pq, new_entry)

    def is_empty(self):
        """
            Returns
            ========
                bool
                    True if the priority queue is empty, False otherwise.
                    
            Note
            =====
                It is possible that the priority queue contains elements but
                is empty. In this case, all elements in the priority queue are
                invalid elements.
        """
        
        return self._size == 0

    def pop(self):
        """
            Returns
            ========
                Node
                    The node with the minimum priority value.
            
            Raises
            =======
                IndexError
                    If the priority queue was empty or did not have any valid
                    elements.
        """

        while self._pq:

            # Pop an entry from the priority queue.
            # If it is not invalid, then return the node.
            _, _, node, state = heapq.heappop(self._pq)
            if state != PriorityQueue._REMOVED_TOKEN:

                self._size -= 1
                del self._state_dict[state]
                return node

        # Popping from an empty priority queue.
        return IndexError("index out of range")
        
    def contains(self, state):
        """
            Parameters
            ===========
                state: State
                    The state to be checked.
                    
            Returns
            ========
                bool
                    True if the state is present in the priority queue, False
                    otherwise.
        """
        
        return state in self._state_dict
