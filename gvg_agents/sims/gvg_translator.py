import copy
from gvg_agents.Search import search
class Translator():
    def __init__(self,abstractClass):
        self.abstract = abstractClass
        return
    
    def update_high_actions(self,actions):
        #just to make sure this is called atleast once
        self.high_actions.update(actions)
    
    def plan_to_state(self,state1,state2,algo="astar"):
        '''
        orientation is not considered for goal check, this is done since
        we need to plan only to abstract states which do not differ by orientation
        '''
        state1_ = copy.deepcopy(state1)
        state2_ = copy.deepcopy(state2)
        action_dict = self.get_successor(state1_)
        action_list,total_nodes_expanded = search(state1_,state2_,self,algo,custom_g=False)
        return action_list,total_nodes_expanded
        #print(plot_state(state2))
        #print("Plan:"+str(action_list))
    
    def iaa_query(self,abs_state,plan):
        '''
            state: abstract
            plan: hashed values corresponding to stored actions
        '''
        if self.validate_state(abs_state):            
            state  = copy.deepcopy(abs_state)
            for i,action in enumerate(plan):
                '''
                    can check plan possibility here itself
                    if subsequent states are not equal, can't execute
                '''
                can_execute,abs_after = self.execute_from_ID(state,action)
                if can_execute:
                    state = abs_after
                else:
                    return False,i,abs_after #check from sokoban code
            return True,len(plan),abs_after #check from sokoban code
        else:
            return False,0,abs_state
    
    def get_ground_state(self,state):
        gstate = self.abstract
        gstate.state = {}
        for k,v in state.state.items():
            if v!=None:
                p = k
                for _v in v:
                    gstate.state[k+"-"+"-".join(list(_v))]=[()]
        gstate.objects = {}
        gstate.rev_objects = {}
        return gstate
    