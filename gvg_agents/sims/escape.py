import logging
import os
import subprocess
import sys
import traceback
import argparse
sys.path.append("src/utils")
sys.path.append("./utils")
sys.path.append("src/lattice/")
from pprint import pprint
from gvg_agents.sims.gvg_translator import Translator
import numpy as np
from collections import defaultdict
from lattice.model_pddl import State
import pickle
import uuid
from func_timeout import func_timeout, FunctionTimedOut
from collections import OrderedDict,defaultdict
from itertools import combinations,permutations,product
import pprint
import random
from config import *
from gvg_agents.Search import search
import copy
from gvg_agents.node import Node
from utils.helpers import state_to_set
pp = pprint.PrettyPrinter(indent=4)
import copy
def save_query(function):
    def _save_query(self,query):
        qkey = str("||".join(sorted(state_to_set(query['init_state'].state)))) + "|||" + str("||".join(query['plan']))
        a,b,c = function(self,query)
        self.queries[qkey] = [a,b,c]
        with open(self.query_history_file,"wb") as f:
            pickle.dump(self.queries,f)
        return a,b,c
    return _save_query

def invert_dictionary(idict):
        odict = defaultdict(list)
        for k,v in idict.items():
            odict[v].append(k)
        return odict

class Action:
    def __init__(self,name,s1,s2):
        self.name = name
        self.header = None
        self.modified_predicates = defaultdict(list)
        self.modified_predicates_typed = defaultdict(list)
        self.state_before= s1
        self.state_after = s2
        self.static_preds = defaultdict(list)
        self.relavant_static_props = {}
        self.static_relations = defaultdict(list)
        self.static_relations_typed = defaultdict(list)
        self.modified_objects = defaultdict(None)
        self.modified_objects_typed = defaultdict(set)
        self.added_predicates = defaultdict(list)
        self.deleted_predicates = defaultdict(list)
    
    def __eq__(self,action):
        #if sorted(list(self.header.values())) == sorted(list(action.header.values())):
        #    return True
        #else:
        #    return False  
        if self.state_before == action.state_before and self.state_after == action.state_after:
             return True
        return False
    
    def assign_predicate_types(self):
        s1_ = copy.deepcopy(self.state_before.state)
        s2_ = copy.deepcopy(self.state_after.state)
        for k,vals in s1_.items():
            if k not in s2_: #pred has been deleted
                #zeroary predicate added:
                if vals == [()]:
                    self.modified_predicates_typed[k].append([()])
                    self.modified_predicates[k] = [()]
                    self.deleted_predicates[k] = [()]
                else:
                    for v in vals:
                        if len(v)!=0:
                            typed_v = []
                            [typed_v.append(self.state_before.rev_objects[t_v]) for t_v in v]
                            self.modified_predicates_typed[k].append(tuple(typed_v))
                            self.modified_predicates[k].append(v)
                            self.deleted_predicates[k].append(v)
            else:
                for v in vals:
                    if v not in s2_[k]: ##CLEAN THIS UP!!!
                        self.modified_predicates[k].append(v)
                        self.deleted_predicates[k].append(v)
                        typed_v = []
                        for t_v in v:
                            typed_v.append(self.state_before.rev_objects[t_v])
                        self.modified_predicates_typed[k].append(tuple(typed_v))
                    else:
                        self.static_preds[k].append(v)
            # if len(self.modified_predicates[k])==0:
            #     self.modified_predicates.pop(k)
        
        for k,vals in s2_.items():
            if k not in s1_: #pred has been deleted
                #zeroary predicate added:
                if vals == [()]:
                    self.modified_predicates_typed[k] = [()]
                    self.modified_predicates[k] = [()]
                    self.added_predicates[k] = [()]
                else:
                    for v in vals:
                        if len(v)!=0:
                            typed_v = []
                            for t_v in v:
                                typed_v.append(self.state_after.rev_objects[t_v]) 
                            self.modified_predicates_typed[k].append(tuple(typed_v))
                            self.modified_predicates[k].append(v)
                            self.added_predicates[k].append(v)
            else:
                #self.modified_predicates[k] = []
                for v in vals:
                    if v not in s1_[k]: ##CLEAN THIS UP!!!
                        self.modified_predicates[k].append(v)
                        self.added_predicates[k].append(v)
                        typed_v = []
                        [typed_v.append(self.state_before.rev_objects[t_v]) for t_v in v]
                        self.modified_predicates_typed[k].append(tuple(typed_v))
        


        for k,vals in self.modified_predicates.items():
            if len(vals)!=0:
                for v in vals:
                    if isinstance(v,str):
                        self.modified_objects[v] = self.state_before.rev_objects[v]
                        self.modified_objects_typed[self.state_before.rev_objects[v]].add(v)
                    else:
                        for r in v:
                            self.modified_objects[r] = self.state_before.rev_objects[r]
                            self.modified_objects_typed[self.state_before.rev_objects[r]].add(r)
        self.header = tuple(sorted(self.modified_objects.values()))
        relavant_static = defaultdict(list)
        #combine these into previous loops
        for pred,vals in self.static_preds.items():
            for v in vals:
                if len(vals) == 0:
                    relavant_static[pred] = [()]
                elif isinstance(v,str):
                    if v in list(self.modified_objects.keys()):
                        relavant_static[pred].append([v])
                elif set(v).issubset(set(self.modified_objects.keys())):
                        relavant_static[pred].append(v)         
            
        self.relavant_static_props = relavant_static
        for k,v in self.relavant_static_props.items():
            for _v in v:
                self.static_relations[tuple(_v)].append(k)
                typed_v = []
                [typed_v.append(self.state_before.rev_objects[t_v]) for t_v in _v]
                self.static_relations_typed[tuple(typed_v)].append(k)

class Escape_State:
    def __eq__(self,state2):
        try:
            # for pred in self.state:
            #     if state2.state[pred]!=self.state[pred]:
            #         return False
            for pred,vals in self.state.items():
                if pred in state2.state:
                    if isinstance(vals,list):
                        if sorted(vals)!=sorted(state2.state[pred]):
                            return False
                    else:
                        if state2.state[pred]!=self.state[pred]:
                            return False        
                else:
                    return False
                    
            if self.rev_objects!=state2.rev_objects:
                return False
            return True
        except AttributeError:
            return False
        
    def __str__(self):
        s = ""
        for k,v in self.state.items():
            if k not in ['leftOf','rightOf','above','below']:
                s+=k+": "+str(v)+"\n"
        return s         
    def __hash__(self):
        return hash(str(self))  
    def __init__(self):
        self.grid_height = 4 #assign dynamically later
        self.grid_width = 4 #assign dynamically later
        self.rev_objects = {}#types: location(cells) ONLY
        self.objects = {}
        self.state = {
            'wall':[],
            'player':[],
            'block':[],
            'hole':[],
            'door':[],
            'player_orientation':[],
            'leftOf': [],
            'rightOf': [],
            'above': [],
            'below': [],
            'escaped':[False],
            'clear':[]
        }
        self.block_mapping={} #block_num:cell_num
        self.g_score = 0 #for search
        self.best_path = None #for search

class AbstractEscapeState(State):
    def __init__(self):
        self.grid_height = 4 #assign dynamically later
        self.grid_width = 4 #assign dynamically later
        self.state = {}
        tstate = {
            'at_0' : [], #player
            'at_1' : [], #block
	        'wall' : [],
	        'is_door':[],#cells which are doors
            'is_hole':[],#cells which are holes
            'leftOf': [],
            'rightOf': [],
            'above': [],
            'below': [],
            'clear':[]
        }
        for k,v in tstate.items():
            self.state[k]=v 
        self.rev_objects = {}#locations(cells),sprites(monster,player,door,key)   
        self.objects = {}
    
    def __hash__(self):
        return hash(str(self))
    def __eq__(self,abstract2):
        '''
            TODO: 
                Check for equivalency, not equality
                But is that required?
        '''
        for pred in self.state:
            if pred in abstract2.state:
                if isinstance(self.state[pred],list):
                    if sorted(abstract2.state[pred])!=sorted(self.state[pred]):
                        return False    
                else:
                    if abstract2.state[pred]!=self.state[pred]:
                        return False
            else:
                return False
        if self.rev_objects!=abstract2.rev_objects:
            return False

        return True

    def __str__(self):
        s = ""
        for k,v in self.state.items():
            if k not in ['leftOf','rightOf','above','below']:
                s+=k+": "+str(v)+"\n"
        return s

class EscapeGVGAgent():
    def __init__(self,r,c,min_walls=2,max_walls = 6,ground_actions = True):
        self.ground_actions = ground_actions
        
        files_dir = "../gvg_agents/files/escape/"+str(r)+'_'+str(c)+"/"
        if not os.path.isdir(files_dir):
            os.mkdir(files_dir)
        
        self.translator = Escape_Translator(ground_actions= ground_actions,files_dir=files_dir)
        #files_dir = "/home/raoshashank/agent_interrogation/GVGAI-master/clients/GVGAI-PythonClient/src/files/"
        #files_dir = "../gvg_agents/files/escape/"
        self.random_states_file = files_dir+"random_states"
        self.traces_file = files_dir+"test_trace"
        self.high_actions_dict = files_dir+"high_actions_dict"
        self.high_traces = files_dir+"high_traces"
        temp_states = []
        self.random_states = []
        self.avg_trace_length = 0.0
        self.num_traces = 0
        num_random_states = 1
        self.ground_to_relational_map = {}
        self.min_walls = min_walls
        self.max_walls = max_walls
        self.r = r
        self.c = c
        self.query_history_file = files_dir + "escape_queries"
        self.queries = {}
        try:
            with open(self.query_history_file,"rb") as f:
                self.queries = pickle.load(f)
        except IOError:
            print("No old queries to load")
        try :
            with open(self.random_states_file,"rb") as f:
                temp_states = pickle.load(f)  
        except IOError:
            temp_states = self.generate_random_states(n = num_random_states, r = r,c = c, abstract = True,random = True, save_trace = True,min_walls=min_walls,max_walls = max_walls,algo="human")
        ###generate additional states for data
        n_extra = 20
        self.load_actions()
        self.combine_actions()
        #self.show_actions()
        temp_states_extra = self.generate_random_states(n = n_extra,r=r,c=c, abstract = True,random = True, save_trace = False,min_walls=min_walls,max_walls = max_walls,add_intermediate=False)
        temp_states.extend(temp_states_extra)
        if ground_actions:
            for state in temp_states:
                temp_gstate = self.translator.get_ground_state(state)
                self.random_states.append(temp_gstate)
                self.ground_to_relational_map[temp_gstate] = state
        else:
            self.random_states = temp_states
        # if len(temp_states) == 0:
        #     self.random_states = self.generate_random_states(n = num_random_states, abstract = True,random = True, save_trace = True)
        # else:
        #     self.random_states = temp_states
        self.action_parameters, self.predicates, _, _, self.objects, self.types, _, _ = self.generate_ds()
        print("number of random states: "+str(len(self.random_states)))
        for st in self.random_states:
            temp_k = []
            for k,v in st.state.items():
                if v == None:
                    temp_k.append(k)
            [st.state.pop(k_,None) for k_ in temp_k]

    def fix_state(self,fixed_preds,state,removed,predTypeMapping):
        fstate = copy.deepcopy(state)
        preds_added = {}
        if removed:
            for pred,v in fixed_preds.items():
                pname = pred.split('-')[0]
                args = pred.split('-')[1:]
                if pname == 'clear':
                    #add wall 
                    fstate['wall-'+str(args[0])] = [()]
                    preds_added['wall-'+str(args[0])] = [()]
                if pname == 'wall':
                    #add clear
                    fstate['clear-'+str(args[0])] = [()]
                    preds_added['clear-'+str(args[0])] = [()]  
                if 'at' in pname:
                    fstate['clear-'+str(args[1])]=[()]
                    preds_added['clear-'+str(args[1])] = [()]
                #if 'is_door' in pname:
                
                if 'is_hole' in pname:
                    fstate['clear-'+str(args[0])] = [()]
                    preds_added['clear-'+str(args[0])] = [()]  
        else:
            fstate.add(fixed_preds)
        return fstate,preds_added


    def show_actions(self,action = None):
        if action!=None:
                v = self.translator.high_actions[action]
                print("------action_name:"+str(action)+"--------")
                print("State before: ")      
                print(self.translator.plot_state(self.translator.refine_abstract_state(v[0])))
                print("State after: ")
                print(self.translator.plot_state(self.translator.refine_abstract_state(v[1])))
        else:            
            for k,v in self.translator.high_actions.items():
                print("------action_name:"+str(k)+"--------")
                print("State before: ")        
                self.translator.plot_state(self.translator.refine_abstract_state(v[0]))
                print("State after: ")
                self.translator.plot_state(self.translator.refine_abstract_state(v[1]))
    
    def get_relational_state(self,state):
        if state in self.ground_to_relational_map:
            return self.ground_to_relational_map[state]
        else:
            rstate = self.translator.get_relational_state(state)
            self.ground_to_relational_map[state] = rstate
            return rstate
    
    #@save_query
    def run_query(self,query):
        qkey = str("||".join(sorted(state_to_set(query['init_state'].state)))) + "|||" + str("||".join(query['plan']))
        if self.queries.get(qkey):
            result = self.queries[qkey]
            return result[0],result[1],result[2]                
    
        if len(self.translator.high_actions)!=0:
            #if 'next_to_monster-' in query['init_state'].state:
            #    print("This")
            #return self.translator.iaa_query(query['init_state'],query['plan'],self.action_objects)           
            state = copy.deepcopy(query['init_state'])
            previous_state = copy.deepcopy(state)
            i = 0
            if self.translator.validate_state(previous_state):
                for action_name in query['plan']:
                    for pred,values in self.action_objects[action_name].added_predicates.items():
                        for val in values:
                            if pred in state.state.keys(): 
                                if val in state.state[pred]:#assuming that added effects are not already in the state
                                    return False,i-1,self.translator.get_ground_state(state)
                                else:
                                    #apply add effect
                                    state.state[pred].append(val)
                            else:
                                state.state[pred] = [val]
                    temp = []
                    for pred,values in self.action_objects[action_name].deleted_predicates.items():
                        if pred in state.state.keys():
                            for val in values:
                                if val not in state.state[pred]: #assuming delete effects should be in state
                                    return False,i-1,self.translator.get_ground_state(state)
                                else:
                                    #apply del effect
                                    state.state[pred].remove(val)
                                    if len(state.state[pred]) == 0:
                                        temp.append(pred)
                        else:
                            self.queries[qkey] = [False,i-1,self.translator.get_ground_state(state)]
                            return False,i-1,self.translator.get_ground_state(state)
                    [state.state.pop(k_,None) for k_ in temp]
                    
                    #action effects applied, now check if we can plan to this state if its valid
                    if self.translator.validate_state(state):
                        #actions,total_nodes_expanded = func_timeout(10, self.translator.plan_to_state, args=(state,final_state))
                        try:
                            actions,total_nodes_expanded = func_timeout(5,self.translator.plan_to_state,args = (self.translator.refine_abstract_state(previous_state),self.translator.refine_abstract_state(state),'custom-astar'))
                        except FunctionTimedOut:
                            print("Search TIMEDOUT")
                            actions,total_nodes_expanded = self.translator.plan_to_state(self.translator.refine_abstract_state(previous_state),self.translator.refine_abstract_state(state),'human') 

                        if actions == None:
                            return False,i-1,self.translator.get_ground_state(state)
                        else:
                            previous_state = copy.deepcopy(state)
                    else:
                        return False,i,self.translator.get_ground_state(state)
                    i+=1
                return True,i,self.translator.get_ground_state(state)


        else:
            print("Actions not stored yet!")
            return False,-1,query['state']

    # def get_more_random_states(self,n=10,save=False,random_walk=True):
    #     return_random = self.generate_random_states(n,abstract=True)
    #     self.random_states.extend(return_random)
    #     if save:
    #         with open(self.random_states_file,"rb") as f:
    #             temp_states = pickle.load(f)  
    #         temp_states.extend(return_random)
    #         with open(self.random_states_file,"wb") as f:
    #             pickle.dump(temp_states,f)  
    #     return return_random

    def validate_state(self,state):
        return self.translator.validate_state(state)

    def solve_game(self,state,_actions=False,algo="custom-astar",full_trace = False):
        states = []
        final_state = self.get_solved_state(state)
        actions = {
        'w':'ACTION_UP',
        'a':'ACTION_LEFT',
        's':'ACTION_DOWN',
        'd':'ACTION_RIGHT'
        }
        test_state = copy.deepcopy(state)
        try:
            #actions,total_nodes_expanded = func_timeout(10, self.translator.plan_to_state, args=(state,final_state))
            actions,total_nodes_expanded = self.translator.plan_to_state(state,final_state,algo,full_trace)
        except FunctionTimedOut:
            print("Search TIMEDOUT")
            if _actions:
                return False,False
            else:
                return False
        states.append(state)
        cstate = copy.deepcopy(state)
        if actions == None:
            #print(plot_state(state))
            print("Unsolvable!")
            if _actions:
                return False,False
            else:
                return False
        #print(plot_state(state))
        print("Solved!")                
        print(actions)
        for a in actions:
            tstate = self.translator.get_next_state(cstate,a)
            cstate=copy.deepcopy(tstate)
            states.append(cstate)
        if not _actions:
            return states
        else:
            return states,actions

    def get_solved_state(self,state):
        #low-level solved state
        #TODO:
        # This is not the exact solved state. Any state where the player is at door will do
        temp_state = copy.deepcopy(state)
        temp_state.state['escaped'] = [True]
        temp_state.state['player']=temp_state.state['door']
        return temp_state

    # def get_random_trace(self,state):
    #     print("Why is pasta here?")
    #     input()
    #     exit(0)
    #     max_len = 50
    #     trace  = []
    #     for _ in range(max_len):
    #         succ = self.translator.get_successor(state)
    #         choice = random.choice(list(succ.keys()))
    #         if state.state['pasta_cooked'] == [True]:
    #             trace.append((succ[choice][1],'ACTION_ESCAPE'))
    #             state = succ[choice][1]
    #             break
    #         else:
    #             trace.append((succ[choice][1],choice))
    #             state = succ[choice][1]
    #     return trace

    def generate_random_states(self,r=4,c=4,n=5,save=True,abstract = False,random = False,save_trace = False,min_walls = 0,add_intermediate=True,max_walls = None,algo = "custom_astar"):
        #load previously pickled states
        try:
            with open(self.random_states_file,"rb") as f:
                old_random_states = pickle.load(f)  
        except IOError:
            pass
            print("File not created!")
            old_random_states = []
        
        if save_trace:
            try:
                with open(self.traces_file,"rb") as f:
                    old_traces = pickle.load(f)  
            except IOError:
                pass
            print("File not created!")
            old_traces = []
            
        #generate initial random states
        initial_random_states = []
        new_traces = []
        for i in range(n):
            initial_random_states.append(self.translator.generate_random_state(r = r,c = c,min_walls=min_walls,max_walls = max_walls))
        if add_intermediate:
            abs_random_states = []
            solved_random_states = []
            num_random_traces = 0 #change this back to 10
            add_rs = []
            #get intermediate states
            for s in initial_random_states:
                st,actions = self.solve_game(s,_actions=True,algo=algo,full_trace = True)
                if st != False:
                    actions.append('ACTION_ESCAPE')
                    solved_random_states.extend(st)
                    new_traces.append(list(zip(st,actions)))
                for _ in range(num_random_traces):
                    tr = self.get_random_trace(s)
                    for (s_,a) in tr:
                        if s_ not in initial_random_states:
                            add_rs.append(s_)      
                    new_traces.append(tr)
            solved_random_states.extend(add_rs)
            #convert new random states to abstract form
            if abstract: 
                for s in solved_random_states:
                    s_ = self.translator.abstract_state(s)
                    if not self.translator.validate_state(s_):
                            print("WWWTTTTFFF!")
                            self.translator.validate_state(s_)
                    # if self.ground_actions:
                    #     #abs_random_states.append(self.translator.get_ground_state(s_))    
                    # else:
                    if s_ not in old_random_states and s_ not in abs_random_states:
                        abs_random_states.append(s_)
                solved_random_states = abs_random_states            
            
            #append to old pickled states
            if save_trace:
                old_traces.extend(new_traces)
                with open(self.traces_file,"wb") as f:
                    pickle.dump(old_traces,f)  
            old_random_states.extend(solved_random_states)    
            final_random = solved_random_states
        else:
            final_random = []
            if abstract:
                for s in initial_random_states:
                    s_ = self.translator.abstract_state(s)
                    if s_ not in old_random_states:
                        final_random.append(s_)
            old_random_states.extend(final_random)
        
        with open(self.random_states_file,"wb") as f:
            pickle.dump(old_random_states,f)  
            
        return final_random
    
    def generate_ds(self):
        if len(self.translator.high_actions)!=0:
            return self.translator.generate_ds()
        else:
            #not created actions yet!
            print("Actions not stored yet")
            return False

    def generate_full_traces(self,n,file):
        '''
            This function generates random states and 
            solves them to get traces (saved to file)
        '''
        self.random_states = []
        traces = []
        for _ in range(n):  
           state = self.translator.generate_random_state() 
           self.random_states.append(self.translator.abstract_state(state))

    def load_actions(self,file=None):        
        if file == None:
            file = self.traces_file
        else:
            print("here")
        #file = "/home/raoshashank/agent_interrogation/GVGAI-master/clients/GVGAI-PythonClient/src/files/test_trace"
        try:
            with open(file,'rb') as f:
                test_trace = pickle.load(f)
        except IOError:
            pass
        new_test_traces = []
        for i,run in enumerate(test_trace):
            sas_trace = []
            first_state = run[0][0]
            objects = first_state.rev_objects
            #monster_mapping = first_state.monster_mapping
            self.avg_trace_length+=len(run)
            for j,(sa1,sa2) in enumerate(zip(run,run[1:])):
                zsa1 = sa1[0]
                zsa2 = sa2[0]
                sas_trace.append([zsa1,sa1[1],zsa2])
            new_test_traces.append(sas_trace)
        high_level_traces = []
        high_level_actions = {} #key: action_id, value: (abs_s1,abs_s2)
        #translator = Zelda_Translator()
        action_number = 0        
        for trace in new_test_traces:
            abs_trace = []
            for s1,a,s2 in trace:
                abs_s1 = self.translator.abstract_state(s1) 
                abs_s2 = self.translator.abstract_state(s2)
                '''
                print("Abstract State1:"+str(abs_s1))
                print("Concretized_state1:"+str(self.translator.refine_abstract_state(abs_s1))) 
                print("-------------") 
                print("Abstract State2:"+str(abs_s2))
                print("Concretized_state2:"+str(self.translator.refine_abstract_state(abs_s2))) 
                print("===============")
                '''
                if abs_s1 != abs_s2:
                    #create a new action
                    action_id = "a"+str(action_number)#str(uuid.uuid1())
                    action_number+=1
                    high_level_actions[action_id] = [abs_s1,abs_s2,]
                    abs_trace.append((abs_s1,action_id,abs_s2))
            high_level_traces.append(abs_trace)
            self.avg_trace_length+=len(abs_trace)
        
        self.num_traces = len(high_level_traces)
        self.avg_trace_length = 0.0
        self.avg_trace_length/=self.num_traces
        
        with open(self.high_actions_dict,"wb") as f:
            pickle.dump(high_level_actions,f)

        with open(self.high_traces,"wb") as f:
            pickle.dump(high_level_traces,f)
        self.translator.update_high_actions(high_level_actions)
        print(len(high_level_traces))
        print(len(high_level_actions))
        print("Saved High-level actions as traces")
               
    def combine_actions(self):
        if len(self.translator.high_actions)==0:
            print("Actions dict not saved yet!")
            return False
        self.actions = {}
        self.action_objects = {}
        for action,s in self.translator.high_actions.items():
            temp_action = Action(action,s[0],s[1])
            temp_action.assign_predicate_types()
            if temp_action not in self.action_objects.values():
                self.actions[action] = s
                self.action_objects[action] = temp_action
                #self.actions[-1].assign_predicate_types()
            else:
                print("Pruned!"+str(action))
            #print("")
        #check if actions can be combined
        def check_merge(action1,action2):
            # print("Actions to combine:")
            # print("---Modified---:")
            # print(action1.modified_predicates)
            # print(action2.modified_predicates)
            # print("----Static:---")
            # print(action1.relavant_static_props)
            # print(action2.relavant_static_props)
            mod_obj_typed = copy.deepcopy(action1.modified_objects_typed)
            fixed_header_objects = {}
            possible_assignments = defaultdict(list)
            all_assignments = []
            #fix objects of action1 to header objects
            for i,typ in enumerate(action1.header):
                fixed_header_objects[mod_obj_typed[typ].pop()] = i
                [possible_assignments[i].append(j) for j in action2.modified_objects_typed[typ]]
            
            #action1_cpy_modified_predicates = []
            action1_cpy_added_predicates = []
            action1_cpy_deleted_predicates = []
            action1_cpy_relavant_static_props = []
            #rename preds to take header object indices for action1 and store in list
            for pred,values in action1.added_predicates.items():
                if len(values[0])!=0: #zeroary predicates. CHECK THIS AGAIN!
                    for v in values:
                        action1_cpy_added_predicates.append(pred+'-'+'|'.join(map(lambda x:str(fixed_header_objects[x]),list(v))))
                else:
                    action1_cpy_added_predicates.append(pred)

            for pred,values in action1.deleted_predicates.items():
                if len(values[0])!=0: #zeroary predicates. CHECK THIS AGAIN!
                    for v in values:
                        try:
                            action1_cpy_deleted_predicates.append(pred+'-'+'|'.join(map(lambda x:str(fixed_header_objects[x]),list(v))))
                        except KeyError:
                            print("")
                else:
                    action1_cpy_deleted_predicates.append(pred)

            for pred,values in action1.relavant_static_props.items():
                if len(values[0])!=0: #zeroary predicates. CHECK THIS AGAIN!
                    for v in values:
                        action1_cpy_relavant_static_props.append(pred+'-'+'|'.join(map(lambda x:str(fixed_header_objects[x]),list(v))))
                else:
                    action1_cpy_relavant_static_props.append(pred)
            
            def invert_dict(idict):
                odict = defaultdict(list)
                for k,v in idict.items():
                    odict[v] = k
                return odict
            _k_,_v_ = zip(*possible_assignments.items())
            for v in product(*_v_):
                d = dict(zip(_k_,v))
                if not len(d.values())>len(set(d.values())):
                    all_assignments.append(invert_dict(d))


            for p in all_assignments:
                temp_a2_added_predicates = []
                temp_a2_deleted_predicates = []
                temp_a2_relavant_static_props = []
                
                for pred,values in action2.added_predicates.items():
                    if len(values[0])!=0: #zeroary predicates. CHECK THIS AGAIN!
                        for v in values:
                            temp_a2_added_predicates.append(pred+'-'+'|'.join(map(lambda x:str(p[x]),list(v))))
                    else:
                        temp_a2_added_predicates.append(pred)

                for pred,values in action2.deleted_predicates.items():
                    if len(values[0])!=0: #zeroary predicates. CHECK THIS AGAIN!
                        for v in values:
                            temp_a2_deleted_predicates.append(pred+'-'+'|'.join(map(lambda x:str(p[x]),list(v))))
                    else:
                        temp_a2_deleted_predicates.append(pred)


                for pred,values in action2.relavant_static_props.items():
                    if len(values[0])!=0: #zeroary predicates. CHECK THIS AGAIN!
                        for v in values:
                            temp_a2_relavant_static_props.append(pred+'-'+'|'.join(map(lambda x:str(p[x]),list(v))))
                    else:
                        temp_a2_relavant_static_props.append(pred)

                if sorted(temp_a2_added_predicates) == sorted(action1_cpy_added_predicates) and sorted(temp_a2_deleted_predicates) == sorted(temp_a2_deleted_predicates) and sorted(temp_a2_relavant_static_props) == sorted(action1_cpy_relavant_static_props):
                    return True

            return False

        self.translator.high_actions = self.actions
        print("Done")

    def bootstrap_model(self):
        abs_preds_test = {}
        abs_actions_test = {}
        pal_tuples_fixed = []
        fix_preds = ['leftOf','rightOf','above','below']
        for action,states in self.translator.high_actions.items():
            s_before = self.translator.get_ground_state(states[0])
            s_after = self.translator.get_ground_state(states[1])
            abs_actions_test[action]={}
            for k,v in s_before.state.items():
                if k.split('-')[0] in fix_preds:
                    abs_preds_test[k] = 0
                    abs_actions_test[action][k] = [Literal.POS,Literal.ABS]
                    pal_tuples_fixed.append((action,k,Location.PRECOND))
            for k,v in s_after.state.items():
                if k.split('-')[0] in fix_preds:
                    abs_preds_test[k] = 0
                    if k in abs_actions_test[action]:
                        abs_actions_test[action][k][1] = Literal.ABS
                    else:
                        abs_actions_test[action][k] = [Literal.ABS,Literal.ABS]
                    pal_tuples_fixed.append((action,k,Location.EFFECTS))
    
        return abs_preds_test, abs_actions_test, pal_tuples_fixed

class Escape_Translator(Translator):
    def __init__(self,level_num = 0,ground_actions=False,files_dir=None):
        # super().__init__('/home/raoshashank/GVGAI-master/examples/gridphysics','escape',level_num)   
        # self.files = "/home/raoshashank/agent_interrogation/GVGAI-master/clients/GVGAI-PythonClient/src/files"
        # self.high_actions = {}
        # self.random_states = []
        # self.ground_actions=ground_actions
        super().__init__(AbstractEscapeState)   
        #self.files = "../gvg_agents/files"
        self.files = files_dir
        self.high_actions = {}
        self.random_states = []
        self.ground_actions=ground_actions

    def update_high_actions(self,actions):
        #just to make sure this is called atleast once
        self.high_actions.update(actions)

    def plot_state(self,state):
        sprites = {
                'wall':'W',
                'player':'A',  
                'hole':'H',
                'block':'B',
                'door':'D',
                }

        x_axis_size = state.grid_height
        y_axis_size = state.grid_width
        data = np.chararray([y_axis_size,x_axis_size],unicode=True)
        for i in range(y_axis_size):
            for j in range(x_axis_size): 
                data[i][j] = '.'
        sprite_locs = {}
        for sprite in sprites:
            locations = state.state.get(sprite)
            for location in locations:
                location = location.replace('cell_','')
                cell_x = int(location.split('_')[0])
                cell_y = int(location.split('_')[1])
                data[cell_x][cell_y] = sprites[sprite]
                if sprite == 'player':
                    #data[cell_x][cell_y] = sprites[sprite]
                    data[cell_x][cell_y] = state.state['player_orientation'][0]
                else:
                    data[cell_x][cell_y] = sprites[sprite]
        print(data.T)
    
    def compute_g(self,algorithm, from_state, to_state):
        if isinstance(from_state,Node):
            from_state = from_state.get_state()
        if isinstance(to_state,Node):
            from_state = goal_state.get_state()
            
        restricted_predicates = ['leftOf','rightOf','above','below','player']
        from_player = from_state.state['player'][0]
        to_player = to_state.state['player'][0]
        from_x = int(from_player.replace('cell_','').split('_')[0])
        from_y = int(from_player.replace('cell_','').split('_')[1])
        to_x = int(to_player.replace('cell_','').split('_')[0])
        to_y = int(to_player.replace('cell_','').split('_')[1])
        editting_distance = 0
        for k,v in to_state.state.items():
            if k not in restricted_predicates:
                for _v in v:
                    if _v not in from_state.state[k]:
                        editting_distance+=1
        return editting_distance + abs(from_x - to_x) + abs(from_y - to_y)

    def validate_state(self,ostate):
        '''
            Given ABSTRACT STATE, validate it
            assuming cell positioning is correct already, those are not to be learnt anyway
        '''
        astate = copy.deepcopy(ostate)
        cell_assigned = []
        sprites = []
        necessary_keys = ['at_0','leftOf','rightOf','above','below']
        if len(set(tuple(necessary_keys)).difference(tuple(astate.state.keys())))>0:
            return False
        #for player presence
        if len(astate.state.get('at_0'))!=1:
            return False    
        cell_assigned.append(astate.state['at_0'][0][1])
        if astate.state.get('is_door') !=None:
            if astate.state['at_0'][0][1] == astate.state['is_door'][0][0]:
                if astate.state.get('escaped')!=[()]:
                    return False
            else:
                cell_assigned.append(astate.state['is_door'][0][0])
        else:
            if astate.state.get('escaped')==[()]:
                return False
        blocks = {}
        if astate.state.get('at_1')!=None:
            for block in astate.state.get('at_1'):
                if block[1] in blocks.values() or block[1] in cell_assigned:
                    return False
                blocks[block[0]] = block[1]
                cell_assigned.append(block[1])
        #cell_assigned.extend(list(blocks.values())[:])
        if astate.state.get('wall')!=None:
            for cell in astate.state.get('wall'):
                if cell[0] in cell_assigned:
                    return False
                cell_assigned.append(cell[0])    
        if astate.state.get('is_hole')!=None:
            for cell in astate.state.get('is_hole'):
                if cell[0] in cell_assigned:
                    return False
                cell_assigned.append(cell[0])    
        #all cells assigned just once uniquely and there is one player and 1 door
        for cell,typ in astate.rev_objects.items():
            if typ == 'location':
                if (cell,) in astate.state['clear'] and cell in cell_assigned:                
                    if astate.state.get('is_door')!=None:
                        if (cell,) not in astate.state.get('is_door'):
                            return False
                if cell not in cell_assigned and (cell,) not in astate.state['clear']:
                    return False
        return True
         
    def abstract_state(self,low_state):
        astate = AbstractEscapeState()
        astate.state['at_0']=[('player0',low_state.state['player'][0])]
        if set(low_state.block_mapping.values())!=set(low_state.state['block']):
            raise Exception
        for block in low_state.block_mapping:
            astate.state['at_1'].append((block,low_state.block_mapping[block]))
        for v in low_state.state['door']:
            if low_state.state['player'] == [v]:
                astate.state['escaped']=[()]
            astate.state['is_door'].append((v,))
        for v in low_state.state['hole']:
            astate.state['is_hole'].append((v,))
        for item in low_state.state['wall']:
            astate.state['wall'].append((item,))
        keys = ['leftOf','rightOf','above','below']
        for key in keys:
            astate.state[key]=low_state.state[key]
        temp = []
        
        for k in low_state.state['clear']:
            astate.state['clear'].append((k,))
        
        for k,v in astate.state.items():
            if v == []:
                temp.append(k)
        for k in temp:
            astate.state.pop(k,None)
        astate.rev_objects = low_state.rev_objects
        astate.grid_width,astate.grid_height = low_state.grid_width,low_state.grid_height
        return astate

    def get_relational_state(self,state):
        rstate = AbstractEscapeState()
        rstate.grid_height = 0
        rstate.grid_width = 0
        for p in state.state:
            pred = p.split('-')[0]
            params = p.replace(pred,'').split('-')[1:]
            if params!=['']:
                v = []
                for _p in params:
                    if len(_p)!=0:
                        v.append(_p) 
                        if 'cell' in _p:
                            x = int(_p.split('_')[1])+1
                            y = int(_p.split('_')[2])+1
                            rstate.grid_height = max(y,rstate.grid_height)
                            rstate.grid_width = max(x,rstate.grid_width)
                            rstate.rev_objects[_p] = 'location'
                        else:
                            rstate.rev_objects[_p] = _p.replace('0','')
                
                rstate.state[pred].append(tuple(v))
            else:
                if rstate.state.get(pred) == None:
                    rstate.state[pred]=[()]
                else:
                    rstate.state[pred].append(tuple([]))
        temp_k = []
        for k,v in rstate.state.items():
            if len(v) == 0:    
                temp_k.append(k)
        [rstate.state.pop(k_,None) for k_ in temp_k]
        return rstate

    def refine_abstract_state(self,abstract_state):
        '''
            Concretize an input abstract state
        '''
        low_state = Escape_State()
        low_state.grid_height,low_state.grid_width = abstract_state.grid_height,abstract_state.grid_width
        low_state.rev_objects = abstract_state.rev_objects
        
        low_state.state['player'] = [abstract_state.state['at_0'][0][1]]
        
        low_state.state['player_orientation'] = ['NORTH']
        d = {
            'at_1' : 'block',
            'is_hole' : 'hole',
            'wall' : 'wall',
            'is_door' : 'door',
            'clear':'clear'
        }
        for k,v in d.items():
            if abstract_state.state.get(k)!=None:
                for _v in abstract_state.state[k]:
                    if k == 'at_1':
                        low_state.state[v].append(_v[1])
                        low_state.block_mapping[_v[0]] = _v[1]        
                    else:
                        low_state.state[v].append(_v[0])
                                    
        if 'escaped' in abstract_state.state:
            low_state.state['escaped'] = [True]

        keys = ['leftOf','rightOf','above','below']
        for key in keys:
            low_state.state[key]=abstract_state.state[key] 

        return low_state

    def generate_ds(self):
        '''
           assume the actions are assigned
        '''
        abstract_model = {}
        action_parameters = {}
        abstract_predicates = {}
        types = {}
        objects = {}
        predTypeMapping = {}
        agent_model ={}
        init_state = None
        for action,states in self.high_actions.items():
            for state in states:
                gstate = self.get_ground_state(state)
                for pred in gstate.state:
                    predTypeMapping[pred]=[]
        
        for action in self.high_actions:
            abstract_model[action] = {}
            action_parameters[action] = []
            agent_model[action]= {}
            for pred in predTypeMapping:
                agent_model[action][pred] = [Literal.ABS,Literal.ABS]

        return action_parameters, predTypeMapping, agent_model, abstract_model, objects, types , None, "escape"

    def is_goal_state(self,current_state,goal_state):
        #modifying this temporarily
        # if current_state.state == goal_state.state:
        #     return True
        for pred,vals in current_state.state.items():
                if isinstance(vals,list):
                    if sorted(vals)!=sorted(goal_state.state[pred]):
                        return False
                else:
                    if goal_state.state[pred]!=current_state.state[pred]:
                        return False      
        return True
    
    def is_final_state(self,current_state,goal_state):
        if current_state.state['escaped'] == [True]:
            return True
        return False

    def get_successor(self,state):
        action_dict = {
        'ACTION_UP':[],
        'ACTION_DOWN':[],
        'ACTION_RIGHT':[],
        'ACTION_LEFT':[]
        }
        for action in action_dict:
            next_state = self.get_next_state(state,action)
            if next_state == state:
                action_dict[action] = [0,state]
            else:
                action_dict[action] = [1,next_state]
        return action_dict

    def get_next_state(self,state,action):
        '''
            given state and action, apply action virtually and get resulting state
            actions: up,down,right,left,use
            input: CookMePasta_State, Action name
            assume only legal actions applied, including no effect
        '''
        def invert_dict(idict):
                odict = defaultdict(list)
                for k,v in idict.items():
                    odict[v] = k
                return odict
        try:
            current_position = state.state['player'][0]
            x = int(current_position.replace('cell_','').split('_')[0])
            y = int(current_position.replace('cell_','').split('_')[-1])
            #assume cell naming convention to avoid searching
            cell_up = 'cell_'+str(x)+'_'+str(y-1)
            cell_up_2 = 'cell_'+str(x)+'_'+str(y-1-1)
            
            cell_down = 'cell_'+str(x)+'_'+str(y+1)
            cell_down_2 = 'cell_'+str(x)+'_'+str(y+1+1)
            
            cell_right = 'cell_'+str(x+1)+'_'+str(y)
            cell_right_2 = 'cell_'+str(x+1+1)+'_'+str(y)
            
            cell_left = 'cell_'+str(x-1)+'_'+str(y)
            cell_left_2 = 'cell_'+str(x-1-1)+'_'+str(y)
            
            if cell_up not in state.rev_objects.keys() or cell_up in state.state['wall']:
                cell_up = None
            if cell_down not in state.rev_objects.keys() or cell_down in state.state['wall']:
                cell_down = None    
            if cell_right not in state.rev_objects.keys() or cell_right in state.state['wall']:
                cell_right = None    
            if cell_left not in state.rev_objects.keys() or cell_left in state.state['wall']:
                cell_left = None

            if cell_up_2 not in state.rev_objects.keys() or cell_up_2 in state.state['wall']:
                cell_up_2 = None
            if cell_down_2 not in state.rev_objects.keys() or cell_down_2 in state.state['wall']:
                cell_down_2 = None    
            if cell_right_2 not in state.rev_objects.keys() or cell_right_2 in state.state['wall']:
                cell_right_2 = None    
            if cell_left_2 not in state.rev_objects.keys() or cell_left_2 in state.state['wall']:
                cell_left_2 = None

            cells = {
                'ACTION_UP':[cell_up,cell_up_2],
                'ACTION_DOWN':[cell_down,cell_down_2],
                'ACTION_RIGHT':[cell_right,cell_right_2],
                'ACTION_LEFT':[cell_left,cell_left_2]
            }
            d = {
                'EAST': cell_right,
                'WEST': cell_left,
                'NORTH': cell_up,
                'SOUTH': cell_down
            }
            d2 = {
                'ACTION_UP' : 'NORTH',
                'ACTION_DOWN': 'SOUTH',
                'ACTION_RIGHT': 'EAST',
                'ACTION_LEFT':'WEST'
            }
            facing_cell = d[state.state['player_orientation'][0]] #cell the player is facing          
        except KeyError as e:
            print("Something wrong with state!")
        sprite_locations = invert_dict(state.block_mapping)
        if state.state.get('door')!=[]:
            sprite_locations[state.state['door'][0]] = 'door'
        for i,hole in enumerate(state.state['hole']):
            sprite_locations[hole] = 'hole'+str(i)

        next_cells = cells[action]
        next_state = copy.deepcopy(state)
        del_items = []

        if d2[action]!= state.state['player_orientation'][0]:
            next_state.state['player_orientation'] = [d2[action]]
            return next_state
        else:
            if next_cells[0]!=None:
                #player can move
                if next_cells[0] in sprite_locations.keys():
                    #player may be able to move the item or move into door
                    if state.state['door'] == [next_cells[0]]:
                        next_state.state['player'] = [next_cells[0]]
                        next_state.state['escaped'] = [True]
                        next_state.state['clear'].append(current_position)
                        return next_state

                    if next_cells[1]!=None and 'block' in sprite_locations[next_cells[0]]: #next_cell[0] is a block
                        #next to next cell is not wall
                        if next_cells[1] in sprite_locations.keys():
                            if 'hole' in sprite_locations[next_cells[1]]:
                                #remove block
                                next_state.state['block'].remove(next_cells[0])
                                #next_state.rev_objects.pop(sprite_locations[next_cells[0]],None)
                                next_state.block_mapping.pop(sprite_locations[next_cells[0]],None)
                                next_state.state['player'] = [next_cells[0]]
                                next_state.state['clear'].append(current_position)
                            else:
                                return next_state #cannot combine and cannot move
                        else:
                            #push item
                            #next_state.state[sprite_locations[next_cells[0]]]=[next_cells[1]]
                            next_state.block_mapping[sprite_locations[next_cells[0]]] = next_cells[1]
                            next_state.state['player'] = [next_cells[0]]
                            next_state.state['block'].remove(next_cells[0])
                            next_state.state['block'].append(next_cells[1])
                            next_state.state['clear'].append(current_position)
                            next_state.state['clear'].remove(next_cells[1])
                    else:
                        return next_state
                else:
                    #just move the agent
                    next_state.state['player'] = [next_cells[0]]
                    next_state.state['clear'].append(current_position)
                    next_state.state['clear'].remove(next_cells[0])
            else:
                #no effect 
                return next_state
        return next_state

    def plan_to_state(self,state1,state2,algo="custom-astar",full_trace = False):
        '''
        orientation is not considered for goal check, this is done since
        we need to plan only to abstract states which do not differ by orientation
        '''
        state1_ = copy.deepcopy(state1)
        state2_ = copy.deepcopy(state2)
        if algo == "human":
            actions = {
            'w':'ACTION_UP',
            'a':'ACTION_LEFT',
            's':'ACTION_DOWN',
            'd':'ACTION_RIGHT',
            'q':'ACTION_EXIT'
            }
            action_list = []
            total_nodes_expanded = 0
            print("Solve this muggle:")
            #only used for full solution
            self.plot_state(state1_)
            self.plot_state(state2_)
            act_string = ''
            while(len(act_string)==0):
                act_string = input()
            use_string = False
            if len(act_string.split(' '))>1:
                act_string = act_string.split(' ')
                use_string = True
            while(True):
                self.plot_state(state1_)
                if not self.validate_state(self.abstract_state(state1_)):
                    print("invalid state wtf?")
                    self.validate_state(self.abstract_state(state1_),verbose = True)
                if not use_string:    
                    action = actions.get(input())
                else:
                    action = actions.get(act_string.pop(0))
                # print(state1_)
                if action==None:
                    continue
                else:
                    if action== 'ACTION_EXIT':
                        action_list = None
                        break
                    action_list.append(action)
                if full_trace:
                    if state1_.state['escaped'][0]:
                        break
                else:
                    if state1_==state2_:
                        break
                state1_ = self.get_next_state(state1_,action)
                
            action_dict = self.get_successor(state1_)
        else:
            action_list,total_nodes_expanded = search(state1_,state2_,self,algo,full_trace,custom_g=True)
            print(action_list)
            # for action in action_list:
            #     print("-----")
            #     self.plot_state(state1_)
            #     state1_ = self.get_next_state(state1_,action)
        
        return action_list,total_nodes_expanded
   
    def get_ground_state(self,state):
        gstate = Escape_State()
        gstate.grid_height,gstate.grid_width = state.grid_height,state.grid_width
        gstate.state = {}
        for k,v in state.state.items():
            if v!=None:
                p = k
                for _v in v:
                    gstate.state[k+"-"+"-".join(list(_v))]=[()]
        gstate.objects = {}
        gstate.rev_objects = {}
        return gstate

    def generate_random_state(self,r=4,c=4,min_walls = 0,max_walls = None):
        random_state = Escape_State()
        random_state.grid_height = r
        random_state.grid_width = c
        if max_walls == None:
            max_walls = int(5 * c * r / 10) 
        while True:
                #try:
                random_state = Escape_State()
                random_state.grid_height = r
                random_state.grid_width =  c
                player_location = 'cell_'+str(np.random.randint(1,c))+'_'+str(np.random.randint(1,r))
                inside_cells = set()
                for i in range(c):
                    for j in range(r): 
                        cell_name = 'cell_'+str(i)+'_'+str(j)
                        if i!=c-1 and j!=r-1 and i!=0 and j!=0: 
                            inside_cells.add(cell_name)
                        cell_up = 'cell_'+str(i)+'_'+str(j-1)
                        cell_down = 'cell_'+str(i)+'_'+str(j+1)
                        cell_right = 'cell_'+str(i+1)+'_'+str(j)
                        cell_left = 'cell_'+str(i-1)+'_'+str(j)
                        random_state.rev_objects[cell_name] = 'location'
                        if i+1<c:
                            if (cell_name,cell_right) not in random_state.state['leftOf']:
                                random_state.state['leftOf'].append((cell_name,cell_right))
                            if (cell_right,cell_name) not in random_state.state['rightOf']:
                                random_state.state['rightOf'].append((cell_right,cell_name))
                        
                        if i!=0:
                            if (cell_left,cell_name) not in random_state.state['leftOf']:
                                random_state.state['leftOf'].append((cell_left,cell_name))
                            if (cell_name,cell_left) not in random_state.state['rightOf']:
                                random_state.state['rightOf'].append((cell_name,cell_left))

                        if j+1<r:
                            if (cell_name,cell_down) not in random_state.state['above']:
                                random_state.state['above'].append((cell_name,cell_down))
                            if (cell_down,cell_name) not in random_state.state['below']:
                                random_state.state['below'].append((cell_down,cell_name))
                    
                        if j!=0:
                            if (cell_up,cell_name) not in random_state.state['above']:
                                random_state.state['above'].append((cell_up,cell_name))
                            if (cell_name,cell_up) not in random_state.state['below']:
                                random_state.state['below'].append((cell_name,cell_up))    
                
                if max_walls!=0:
                    #num_blocked_cells = np.range(min_walls,max_walls),replace = False)
                    num_blocked_cells = min_walls
                else:
                    num_blocked_cells = 0
                all_cells = list(random_state.rev_objects.keys())
                inside_cells = list(inside_cells)
                #walls
                blocked_cells = np.random.choice(all_cells, num_blocked_cells,replace = False)
                all_cells = list(set(tuple(all_cells)).difference(set(tuple(blocked_cells))))
                inside_cells = list(set(tuple(inside_cells)).difference(set(tuple(blocked_cells))))

                num_blocks = int(0.3*len(all_cells))
                num_holes = int(0.2*len(all_cells))
                
                block_cells = np.random.choice(all_cells, num_blocks,replace = False)
                all_cells = list(set(tuple(all_cells)).difference(set(tuple(block_cells))))
                inside_cells = list(set(tuple(inside_cells)).difference(set(tuple(block_cells))))
                
                hole_cells = np.random.choice(all_cells, num_holes,replace = False)
                all_cells = list(set(tuple(all_cells)).difference(set(tuple(hole_cells))))
                inside_cells = list(set(tuple(inside_cells)).difference(set(tuple(hole_cells))))
                
                #player
                player_position = np.random.choice(all_cells,replace = False)
                random_state.rev_objects['player0']='player'
                all_cells.remove(player_position)
                #inside_cells.remove(player_position)
                [random_state.state['wall'].append(blocked_cells[i]) for i in range(len(blocked_cells))]
                for i in range(len(block_cells)):
                    random_state.state['block'].append(block_cells[i])
                    random_state.block_mapping['block'+str(i)] = block_cells[i]
                    random_state.rev_objects['block'+str(i)] = 'block'
                [random_state.state['hole'].append(hole_cells[i]) for i in range(len(hole_cells))]
                
                random_state.state['player'].append(player_position)               
                door_position = np.random.choice(all_cells,replace=False)
                random_state.rev_objects['door0'] = 'door'
                all_cells.remove(door_position)
                #inside_cells.remove(door_position)
                random_state.state['door'].append(door_position)
                random_state.state['player_orientation'] = ['EAST']
                random_state.objects = invert_dictionary(random_state.rev_objects)
                
                [random_state.state['clear'].append(all_cells[i]) for i in range(len(all_cells))]
                random_state.state['clear'].append(door_position)
                
                self.plot_state(random_state)
                #print(random_state)
                #print(random_state.block_mapping)
                if self.validate_state(self.abstract_state(random_state)):
                    break
                else:
                    self.validate_state(self.abstract_state(random_state))
                # except ValueError as e:
                #     print("Stupid sampling error")
                #     pass
            
        return random_state