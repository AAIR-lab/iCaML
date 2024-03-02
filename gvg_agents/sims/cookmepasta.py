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

def compare_dict(d1,d2):
    in_d1_only = defaultdict(list)
    in_d2_only = defaultdict(list)
    
    for pred,values in d1.items():
        if pred not in d2:
            in_d1_only[pred] = values
        else:
            for v in values:
                if v not in d2[pred]:
                    in_d1_only[pred].append(v)
    for pred,values in d2.items():
        if pred not in d1:
            in_d2_only[pred] = values
        else:
            for v in values:
                if v not in d1[pred]:
                    in_d2_only[pred].append(v)
    
    print("in first dict only:")
    print(in_d1_only)
    print("in second dict only:")
    print(in_d2_only)
    
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

class AbstractCookMePastaState(State):
    def __init__(self):
        self.grid_height = 4 #assign dynamically later
        self.grid_width = 4 #assign dynamically later
        self.state = {
            'at_0' : [],
            'at_1' : [],
            'at_2' : [],
            'at_3' : [],
            'at_4' : [],
            'at_5' : [],
            'at_6' : [],
            'at_7' : [],
            'pasta_cooked':[], #zeroary
	        'leftOf': [],
            'rightOf': [],
            'above': [],
            'below': [],
            'wall':[],
            'clear':[]
        }
        #for k,v in tstate.items():
        #    self.state[k]=v 
        self.rev_objects = {} #locations(cells),sprites(monster,player,door,key)   
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

class CookMePasta_State:
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
            #'key':[], 
            #'lock':[],
            #'has_key':[],
            'wall':[],
            'player':[],
            'raw_pasta':[],
            'boiling_water':[],
            'tomato':[],
            'tuna':[],
            'pasta_in_place':[],
            'sauce_in_place':[],
            'pasta_done':[], #finished item
            'pasta_cooked':[False],
            'leftOf': [],
            'rightOf': [],
            'above': [],
            'below': [],
            'clear':[],
            'player_orientation':[]
        }
        self.g_score = 0 #for search
        self.best_path = None #for search     

def saved_plan(function):
    def _saved_plan(self,state1,state2,algo,full_trace=False):
        pkey = str("||".join(sorted(state_to_set(state1.state)))) + "|||" + str("||".join(sorted(state_to_set(state2.state))))
        if self.saved_plans.get(pkey)!=None:
            return self.saved_plans.get(pkey) 
        a,b = function(self,state1,state2,algo,full_trace)
        self.saved_plans[pkey] = [a,b]
        with open(self.plan_history_file,"wb") as f:
            pickle.dump(self.saved_plans,f)
        return a,b
    return _saved_plan

class CookMePastaGVGAgent():
    def __init__(self,r,c,min_walls=2,max_walls = 3,ground_actions = True):
        self.ground_actions = ground_actions
        #files_dir = "../gvg_agents/files/cookmepasta/"
        files_dir = "../gvg_agents/files/cookmepasta/"+str(r)+'_'+str(c)+"/"
        if not os.path.isdir(files_dir):
            os.mkdir(files_dir)
        self.translator = CookMePasta_Translator(ground_actions= ground_actions,files_dir=files_dir)
        #files_dir = "/home/raoshashank/agent_interrogation/GVGAI-master/clients/GVGAI-PythonClient/src/files/"
        #files_dir = "../gvg_agents/files/cookmepasta/"
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
        self.query_history_file = files_dir + "cookmepasta_queries"
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
            temp_states = self.generate_random_states(n = num_random_states,r = r,c = c, abstract = True,random = True, save_trace = True,min_walls=min_walls,max_walls = max_walls,algo="human")
        ###generate additional states for data
        n_extra = 30
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
    @save_query
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
                                if val in state.state[pred]:
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
                                if val not in state.state[pred]:
                                    return False,i-1,self.translator.get_ground_state(state)
                                else:
                                    #apply del effect
                                    state.state[pred].remove(val)
                                    if len(state.state[pred]) == 0:
                                        temp.append(pred)
                        else:
                            return False,i-1,self.translator.get_ground_state(state)
                    [state.state.pop(k_,None) for k_ in temp]
                    
                    #action effects applied, now check if we can plan to this state if its valid
                    if self.translator.validate_state(state):
                        try:
                            actions,total_nodes_expanded = func_timeout(20,self.translator.plan_to_state,args = (self.translator.refine_abstract_state(previous_state),self.translator.refine_abstract_state(state),'custom-astar'))
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

    def solve_game(self,state,_actions=False,algo="custom-astar"):
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
            actions,total_nodes_expanded = self.translator.plan_to_state(state,final_state,algo)
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
        temp_state = copy.deepcopy(state)
        temp_state.state['pasta_cooked'] = [True]
        temp_state.state['raw_pasta']=[]
        temp_state.state['boiling_water']=[]
        temp_state.state['tomato']=[]
        temp_state.state['tuna']=[]
        del_list = ['raw_pasta0','boiling_water0','tomato0','tuna0','pasta_in_place0','sauce_in_place0']
        [temp_state.rev_objects.pop(k,None) for k in del_list]
        temp_state.state['pasta_in_place']=[]
        temp_state.state['sauce_in_place']=[]
        temp_state.state['pasta_done']=[]
        all_cells = temp_state.objects['location']
        temp_state.rev_objects['pasta_done0']='pasta_done'
        temp_state.objects['pasta_done']=['pasta_done0']
        temp_state.objects['pasta_in_place']=['pasta_in_place0']
        temp_state.objects['sauce_in_place']=['sauce_in_place0']
        walls = temp_state.state['wall']
        free_cells = set(all_cells).difference(set(walls).union(set(temp_state.state['player'])))
        final_cell = np.random.choice(np.array(list(free_cells)),replace = False)
        free_cells.remove(final_cell)
        temp_state.state['pasta_done'] = [final_cell]
        temp_state.state['clear'] = list(free_cells)
        #print(plot_state(state))
        return temp_state

    def get_random_trace(self,state):
        max_len = 50
        trace  = []
        for _ in range(max_len):
            succ = self.translator.get_successor(state)
            choice = random.choice(list(succ.keys()))
            if state.state['pasta_cooked'] == [True]:
                trace.append((succ[choice][1],'ACTION_ESCAPE'))
                state = succ[choice][1]
                break
            else:
                trace.append((succ[choice][1],choice))
                state = succ[choice][1]
        return trace

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
                st,actions = self.solve_game(s,_actions=True,algo=algo)
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
                    #abs_random_states.append(self.translator.get_ground_state(s_))    
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
                    print(self.translator.plot_state(s))
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

class CookMePasta_Translator(Translator):
    def __init__(self,ground_actions=False,files_dir=None):
        # super().__init__('/home/raoshashank/GVGAI-master/examples/gridphysics','cookmepasta',level_num)   
        # self.level_file_root  = "/home/raoshashank/GVGAI-master/examples/gridphysics/"
        # self.files = "/home/raoshashank/agent_interrogation/GVGAI-master/clients/GVGAI-PythonClient/src/files"
        # self.high_actions = {}
        # self.random_states = []
        # self.ground_actions=ground_actions
        super().__init__(AbstractCookMePastaState)   
        #self.files = "../gvg_agents/files"
        self.files = files_dir
        self.high_actions = {}
        self.random_states = []
        self.ground_actions=ground_actions
        self.saved_plans = {}
        self.plan_history_file = files_dir + "cookempasta_plans"

    def update_high_actions(self,actions):
        #just to make sure this is called atleast once
        self.high_actions.update(actions)

    def plot_state(self,state):
        sprites = {
                'wall':'W',
                'player':'A',  
                'raw_pasta':'R',
                'boiling_water':'B',
                'tomato':'O',
                'tuna':'T',
                'pasta_in_place':'P',
                'sauce_in_place':'S',
                'pasta_done':'F',
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
        #each cell should have only 1 thing in it
        #if either tuna or tomato are missing, sauce_in_place should be present
        #if either raw_pasta or boiling_water is missing, pasta_in_place should be present
        #if only 2 "at" are present, it should be pasta_done and player
        #if only 3 "at" is present, it should be pasta_in_place, sauce_in_place and player
        #if none of pasta_done or pasta_in_place or sauce_in_place are present, all ingredients should be present
        #if pasta_done is present, pasta_cooked should be true
        # incredients = {
        #     'tomato':
        #     'tuna':
        #     'raw_pasta':
        #     'boiling_water':
        # }
        # half_cooked = {
        #     'pasta_in_place':
        #     'sauce_in_place':
        # }
        astate = copy.deepcopy(ostate)
        sprites = []
        necessary_keys = ['at_0','leftOf','rightOf','above','below']
        if len(set(tuple(necessary_keys)).difference(tuple(astate.state.keys())))>0:
            return False
        #for player presence
        if len(astate.state.get('at_0'))!=1:
            return False    
        cell_assigned = []
        sprites = ['player','tuna','tomato','raw_pasta','boiling_water','pasta_in_place','sauce_in_place','pasta_done']
        sprite_locs = {}
        ats = set()
        for k,v in astate.state.items():
            if 'at_' in k:
                num = int(k.replace('at_',''))
                ats.add(num)
                if num == len(sprites): #pasta_done
                    if astate.state.get('pasta_cooked')==None:
                        return False
                if len(v)>1:
                    return False
                if v[0][1] in cell_assigned:
                    return False
                
                cell_assigned.append(v[0][1])
                sprite_locs[sprites[num]] = v[0][1]
            if k == 'wall':
                for cell in v:
                    if cell[0] in cell_assigned:
                        return False
                    cell_assigned.append(cell[0])    
    
        if astate.state.get('pasta_cooked')==[()]:
            if sprite_locs.get('pasta_done')==None:
                return False
        else:
            if sprite_locs.get('pasta_done')!=None:
                return False
    
        # if sorted(list(ats)) not in [[0,1,2,3,4],[0,1,2,5],[0,3,4,6],[0,5,6],[0,7]]:
        #     return False
        # if (len(sprite_locs)==2 and sorted(list(sprite_locs.keys()))!=['pasta_done','player']) or (len(sprite_locs) == 3 and sorted(list(sprite_locs.keys()))!=['pasta_in_place','player','sauce_in_place']):
        #         return False
        # if len(set(sprite_locs.keys()).difference(set(['pasta_in_place','sauce_in_place','pasta_done'])))==0 and len(set(['tuna','tomato','raw_pasta','boiling_water']).difference(sprite_locs.keys()))==0:
        #     return False

        if len(astate.rev_objects)==0:
            print("Empty")
        
        for cell,typ in astate.rev_objects.items():
            if typ == 'location':
                if (cell,) in astate.state['clear'] and cell in cell_assigned:
                    return False
                if cell not in cell_assigned and (cell,) not in astate.state['clear']:
                    return False

        return True
         
    def abstract_state(self,low_state):
        astate = AbstractCookMePastaState()
        keys = ['player','tuna','tomato','raw_pasta','boiling_water','pasta_in_place','sauce_in_place','pasta_done']
        for i,item in enumerate(keys):
            location = low_state.state.get(item)
            if location!=[]:
                astate.state['at_'+str(i)]=[(item+"0",location[0])] #handling grounding like this for now since only 1 of each is ever present
                if item == 'pasta_done':
                    astate.state['pasta_cooked'] = [()]
        for item in low_state.state['wall']:
            astate.state['wall'].append((item,))
        keys = ['leftOf','rightOf','above','below']
        for key in keys:
            astate.state[key]=low_state.state[key]
        temp = []
        
        for k in low_state.state['clear']:
            astate.state['clear'].append((k,))
        
        for k,v in  astate.state.items():
            if v == []:
                temp.append(k)
        for k in temp:
            astate.state.pop(k,None)
        astate.rev_objects = low_state.rev_objects
        astate.grid_width,astate.grid_height = low_state.grid_width,low_state.grid_height
        return astate

    def get_relational_state(self,state):
        rstate = AbstractCookMePastaState()
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
                            rstate.rev_objects[_p] = 'location'
                            rstate.grid_height = max(rstate.grid_height,y)
                            rstate.grid_width = max(rstate.grid_height,x)
                        else:
                            rstate.rev_objects[_p] = _p.replace('0','')
                
                rstate.state[pred].append(tuple(v))
            else:
                if rstate.state[pred] == None:
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
        low_state = CookMePasta_State()
        low_state.grid_height,low_state.grid_width = abstract_state.grid_height,abstract_state.grid_width
        low_state.rev_objects = abstract_state.rev_objects
        for k,v in abstract_state.state.items():
            if 'at_' in k:
                item = v[0][0]
                location = v[0][1]
                item = item.replace('0','')
                low_state.state[item] = [location]
            elif k == 'pasta_cooked':
                low_state.state['pasta_cooked'] = [True]
            elif k =='wall' or k == 'clear':
                for _v in v:
                    low_state.state[k].append(_v[0])
            else:
                low_state.state[k] = v
        low_state.state['player_orientation'] = ['NORTH']
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
        
        # for state in self.random_states:
        #     gstate = self.get_ground_state(self.abstract_state(state))
        #     for pred in gstate.state:
        #         if pred not in predTypeMapping:
        #             predTypeMapping[pred]=[]

        for action in self.high_actions:
            abstract_model[action] = {}
            action_parameters[action] = []
            agent_model[action]= {}
            for pred in predTypeMapping:
                agent_model[action][pred] = [Literal.ABS,Literal.ABS]

        return action_parameters, predTypeMapping, agent_model, abstract_model, objects, types , None, "cookmepasta_GVG"

    def is_goal_state(self,current_state,goal_state):
        #modifying this temporarily
        # if current_state.state == goal_state.state:
        #     return True
        for pred,v in current_state.state.items():
            if pred in goal_state.state:
                if isinstance(v,list):
                    if sorted(v)!=sorted(goal_state.state[pred]):
                        return False
                else:
                    if v!=goal_state.state[pred]:
                        return False
            else:
                return False
        return True
    
    def is_final_state(self,current_state,goal_state):
        if current_state.state['pasta_done'] == [True]:
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
            d2_r = {
                'NORTH':'ACTION_UP' ,
                'SOUTH':'ACTION_DOWN',
                'EAST':'ACTION_RIGHT',
                'WEST':'ACTION_LEFT'
            }
            #keys = state.state['key']
            #doors = state.state['door']   
            facing_cell = d[state.state['player_orientation'][0]] #cell the player is facing          
            orientation = state.state['player_orientation']        
        except KeyError as e:
            print("Something wrong with state!")

        
        raw_pasta_location = state.state.get('raw_pasta')
        boiling_water_location = state.state.get('boiling_water')
        tomato_location = state.state.get('tomato')
        tuna_location  = state.state.get('tuna')
        pasta_in_place_location = state.state.get('pasta_in_place')
        sauce_in_place_location = state.state.get('sauce_in_place')
        pasta_done_location = state.state.get('pasta_done')

        sprite_locations = {}
        if raw_pasta_location!=[]:
            sprite_locations[raw_pasta_location[0]]='raw_pasta'
        if boiling_water_location!=[]:
            sprite_locations[boiling_water_location[0]]='boiling_water'
        if tomato_location!=[]:
            sprite_locations[tomato_location[0]]='tomato'
        if tuna_location!=[]:
            sprite_locations[tuna_location[0]]='tuna'
        if pasta_in_place_location!=[]:
            sprite_locations[pasta_in_place_location[0]]='pasta_in_place'
        if sauce_in_place_location!=[]:
            sprite_locations[sauce_in_place_location[0]]='sauce_in_place'
        if pasta_done_location!=[]:
            sprite_locations[pasta_done_location[0]]='pasta_done'


        # sprite_locations = {
        #     raw_pasta_location:'raw_pasta',
        #     boiling_water_location:'boiling_water',
        #     tomato_location:'tomato',
        #     tuna_location:'tuna',
        #     pasta_in_place_location:'pasta_in_place',
        #     sauce_in_place_location:'sauce_in_place'
        # }

        combinations = {}
        if raw_pasta_location!=[] and boiling_water_location!=[]:
            combinations[str(raw_pasta_location[0])+'-'+str(boiling_water_location[0])] ='pasta_in_place'
            combinations[str(boiling_water_location[0])+'-'+str(raw_pasta_location[0])] ='pasta_in_place'
        if tuna_location!=[] and tomato_location!=[]:
            combinations[str(tuna_location[0])+'-'+str(tomato_location[0])] ='sauce_in_place'
            combinations[str(tomato_location[0])+'-'+str(tuna_location[0])] ='sauce_in_place'
        if pasta_in_place_location!=[] and sauce_in_place_location!=[]:
            combinations[str(pasta_in_place_location[0])+'-'+str(sauce_in_place_location[0])] ='pasta_done'
            combinations[str(sauce_in_place_location[0])+'-'+str(pasta_in_place_location[0])] ='pasta_done'
        
        # combinations = {
        #     str(raw_pasta_location)+'-'+str(boiling_water_location):'pasta_in_place',
        #     str(boiling_water_location)+'-'+str(raw_pasta_location):'pasta_in_place',
        #     str(tuna_location)+'-'+str(tomato_location):'sauce_in_place',
        #     str(tomato_location)+'-'+str(tuna_location):'sauce_in_place',
        #     str(pasta_in_place_location)+'-'+str(sauce_in_place_location):'pasta_done',
        #     str(sauce_in_place_location)+'-'+str(pasta_in_place_location):'pasta_done'
        # }

        next_cells = cells[action]
        next_state = copy.deepcopy(state)
        del_items = []

        if d2.get(action)!= state.state['player_orientation'][0] and action!='ACTION_USE':#change orientation
            next_state.state['player_orientation'] = [d2[action]]
            return next_state

        if next_cells[0]!=None:
            #player can move
            if next_cells[0] in sprite_locations.keys():
                #player may be able to move the item
                if next_cells[1]!=None:
                    #player may be able to combine
                    if next_cells[1] in sprite_locations.keys():
                        combine = combinations.get(str(next_cells[0])+'-'+str(next_cells[1]))
                        if combine!=None:
                            #can combine items
                            next_state.state[combine] = [next_cells[1]]
                            next_state.rev_objects[combine+'0']=combine
                            del_items.append(sprite_locations[next_cells[0]]+'0')
                            del_items.append(sprite_locations[next_cells[1]]+'0')
                            next_state.objects[combine]=[combine+'0']
                            next_state.state[sprite_locations[next_cells[0]]]=[]
                            next_state.state[sprite_locations[next_cells[1]]]=[]
                            next_state.state['player'] = [next_cells[0]]
                            
                            next_state.state['clear'].append(current_position)
                            #next_state.state['clear'].remove(next_cells[0])
                            
                            #combine = None means cannot combine, thus no movement
                            [next_state.rev_objects.pop(k,None) for k in del_items]
                        else:
                            return next_state #cannot combine and cannot move
                    else:
                        #push item
                        next_state.state[sprite_locations[next_cells[0]]]=[next_cells[1]]
                        next_state.state['player'] = [next_cells[0]]
                        next_state.state['clear'].append(current_position)
                        next_state.state['clear'].remove(next_cells[1])
                        #next_state.state['clear'].remove(next_cells[1])
                        
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
        pasta_done = next_state.state.get('pasta_done') 
        if pasta_done!=[]:
            next_state.state['pasta_cooked'] = [True]
        '''
        if current_position in keys:
            next_state.state['key'].remove(current_position)
            next_state.state['has_key'] = [True]
        '''
        return next_state

    @saved_plan
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
            'd':'ACTION_RIGHT'
            }
            action_list = []
            total_nodes_expanded = 0
            print("Solve this muggle:")
            #self.plot_state(state1_)
            self.plot_state(state2_)
            print("=========")
            while(True):
                self.plot_state(state1_)
                if state1_==state2_:
                    break
                action = actions.get(input())
                if action==None:
                    continue
                else:
                    action_list.append(action)
                state1_ = self.get_next_state(state1_,action)
            
            action_dict = self.get_successor(state1_)
        else:
            action_list,total_nodes_expanded = search(state1_,state2_,self,algo,full_trace,custom_g = True)
            print(action_list)
            # for action in action_list:
            #     print("-----")
            #     self.plot_state(state1_)
            #     state1_ = self.get_next_state(state1_,action)
        
        return action_list,total_nodes_expanded
   
    def get_ground_state(self,state):
        gstate = CookMePasta_State()
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
        random_state = CookMePasta_State()
        random_state.grid_height = r
        random_state.grid_width = c
        if max_walls == None:
            max_walls = int(5 * c * r / 10)
        
        while True:
                try:
                    random_state = CookMePasta_State()
                    random_state.grid_height = r
                    random_state.grid_width =  c
                    player_location = 'cell_'+str(np.random.randint(1,c))+'_'+str(np.random.randint(1,r))
                    inside_cells = set()
                    random_state.state['player_orientation'] = ['NORTH']
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
                        num_blocked_cells = np.random.choice(range(min_walls,max_walls),replace = False)
                    else:
                        num_blocked_cells = 0
                    all_cells = list(random_state.rev_objects.keys())
                    inside_cells = list(inside_cells)
                    #walls
                    blocked_cells = np.random.choice(all_cells, num_blocked_cells,replace = False)
                    all_cells = list(set(tuple(all_cells)).difference(set(tuple(blocked_cells))))
                    inside_cells = list(set(tuple(inside_cells)).difference(set(tuple(blocked_cells))))
                    #player
                    player_position = np.random.choice(all_cells,replace = False)
                    random_state.rev_objects['player0']='player'
                    all_cells.remove(player_position)
                    if player_position in inside_cells: inside_cells.remove(player_position)
                    
                    [random_state.state['wall'].append(blocked_cells[i]) for i in range(len(blocked_cells))]
                    random_state.state['player'].append(player_position)
                    
                    #raw_pasta
                    raw_pasta_position = np.random.choice(inside_cells,replace=False)
                    random_state.rev_objects['raw_pasta0'] = 'raw_pasta'
                    all_cells.remove(raw_pasta_position)
                    inside_cells.remove(raw_pasta_position)
                    random_state.state['raw_pasta'].append(raw_pasta_position)
                    
                    #boiling_water
                    boiling_water_position = np.random.choice(inside_cells,replace=False)
                    random_state.rev_objects['boiling_water0'] = 'boiling_water'
                    all_cells.remove(boiling_water_position)
                    inside_cells.remove(boiling_water_position)
                    random_state.state['boiling_water'].append(boiling_water_position)

                    #tomato
                    tomato_position = np.random.choice(inside_cells,replace=False)
                    random_state.rev_objects['tomato0'] = 'tomato'
                    all_cells.remove(tomato_position)
                    inside_cells.remove(tomato_position)
                    random_state.state['tomato'].append(tomato_position)

                    #tuna
                    tuna_position = np.random.choice(inside_cells,replace=False)
                    random_state.rev_objects['tuna0'] = 'tuna'

                    all_cells.remove(tuna_position)
                    inside_cells.remove(tuna_position)
                    random_state.state['tuna'].append(tuna_position)
                    
                    [random_state.state['clear'].append(all_cells[i]) for i in range(len(all_cells))]
                    
                    random_state.rev_objects['sauce_in_place0'] = 'sauce_in_place'
                    random_state.rev_objects['pasta_in_place0'] = 'pasta_in_place'
                    random_state.rev_objects['pasta_done0'] = 'pasta_done'
                    #random_state.state['key'].append(key_position)
                    #random_state.state['door'].append(door_position)
                    # random_state.state['has_key'] = [False]
                    
                    random_state.objects = invert_dictionary(random_state.rev_objects)
                    if self.validate_state(self.abstract_state(random_state)):
                        break
                    else:
                        print("Failed to generate")
                except ValueError as e:
                    pass  
        return random_state
