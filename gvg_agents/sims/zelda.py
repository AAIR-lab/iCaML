import logging
import os
import subprocess
import sys
import traceback
import argparse
sys.path.append("src/utils")
sys.path.append("./utils")
sys.path.append("src/lattice/")
sys.path.append("src/query/")
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
from query.po_query import *
from post_processing import call_planner,ExecuteSimplePlan
from utils.parse_files import generate_ds
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

def saved_state(function):
    def _saved_state(self,fixed_preds,state):
        #pkey = str("||".join(sorted(state_to_set(state))))
        pkey = str("||".join(sorted(state_to_set(fixed_preds))))
        if self.saved_correct_states.get(pkey)!=None:
            return self.saved_correct_states.get(pkey) 
        a = function(self,fixed_preds,state)
        self.saved_correct_states[pkey] = [a]
        with open(self.saved_correct_states_file,"wb") as f:
            pickle.dump(self.saved_correct_states,f)
        return a
    return _saved_state


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

IDs = {
    11:'MONSTER',
    0:'WALL',
    7:'PLAYER',
    3:'DOOR',
    4:'KEY',
    8:'PLAYER_WITH_KEY',
    5:'SWORD',
    1:'CLEAR'
    }
def returnNone():
    return None
class AbstractZeldaState(State):
    def __init__(self):
        self.grid_height = 4 #assign dynamically later
        self.grid_width = 4 #assign dynamically later
        self.state = defaultdict(returnNone)
        tstate = {
            'at_0' : [], #player
            'at_1' : [],#key
            'at_2' : [],#monster
            'at_3' : [],#door
	        'monster_alive' : [],
            #'has_key' : [],
            #'escaped' : [],
            'wall' : [],
	        #'is_player' : [],
	        #'is_monster': [],
            #'is_key' : [],
            #'is_door':[],
            'leftOf': [],
            'rightOf': [],
            'above': [],
            'below': [],
            'next_to_monster':[], #as of now only 1 monster in domain
            'clear':[]
        }
        for k,v in tstate.items():
            self.state[k]=v 
        self.rev_objects = {}#locations(cells),monster,player,door,key
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
       
def invert_dictionary(idict):
        odict = defaultdict(list)
        for k,v in idict.items():
            odict[v].append(k)
        return odict

class Zelda_State:
    def __eq__(self,state2):
        try:
            for pred,vals in self.state.items():
                if isinstance(vals,list):
                    if sorted(vals)!=sorted(state2.state[pred]):
                        return False
                else:
                    if state2.state[pred]!=self.state[pred]:
                        return False
            # if self.state!=state2.state:
            #     return False
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
        self.monster_id = 11
        self.wall_id = 0
        self.player_id = 7
        self.door_id = 3
        self.key_id = 4
        self.player_with_key_id = 8
        self.grid_height = 4 #assign dynamically later
        self.grid_width = 4 #assign dynamically later
        self.rev_objects = {}#types: location(cells) ONLY
        self.objects = {}
        #self.monster_mapping=monster_mapping #key:monster name, value: original monster-location
        #self.trace_id=trace_id
        self.state = {
            'wall':[],
            'player':[],
            'monster':[],
            'key':[],
            'door':[],
            'player_orientation':[],
            'has_key':[False],
            'leftOf': [],
            'rightOf': [],
            'above': [],
            'below': [],
            'escaped':[False],
            'clear':[]
        }
        self.g_score = 0 #for search
        self.best_path = None #for search 
    
def save_query(function):
    def _save_query(self,query):
        qkey = str("||".join(sorted(state_to_set(query['init_state'].state)))) + "|||" + str("||".join(query['plan']))
        a,b,c = function(self,query)
        self.queries[qkey] = [a,b,c]
        with open(self.query_history_file,"wb") as f:
            pickle.dump(self.queries,f)
        return a,b,c
    return _save_query

class Zelda_Translator(Translator):
    def __init__(self,ground_actions=False,files_dir=None):
        super().__init__(AbstractZeldaState)   
        #self.files = "../gvg_agents/files"
        self.files = files_dir
        self.high_actions = {}
        self.random_states = []
        self.ground_actions=ground_actions
        self.saved_plans = {}
        self.plan_history_file = files_dir + "zelda_plans"
    
    # def plot_abs_state(self,astate):
    #     sprites = {
    #             "goal": 'g', 
    #             "key": '+',         
    #             "nokey": 'A', 
    #             "monsterQuick": '1', 
    #             "monsterNormal": '2', 
    #             "monsterSlow": '3', 
    #             "wall":"w",
    #             "floor":".",
    #             "withkey":"Q"
    #         }
    #     x_axis_size = astate.grid_height
    #     y_axis_size = astate.grid_width
    #     data = np.chararray([y_axis_size,x_axis_size],unicode=True)
    #     for i in range(y_axis_size):
    #         for j in range(x_axis_size): 
    #             data[i][j] = sprites["floor"]
        
    #     for v in astate.state['at']:
    #         cell = v[1]
    #         i = int(cell.replace('cell_','').split('_')[0])
    #         j = int(cell.replace('cell_','').split('_')[1])
    #         sprite = v[0]
    #         if (sprite,) in astate.state['is_player']:
    #             data[i][j] = sprites['nokey']
    #             if 'has_key' in astate.state.keys():
    #                 data[i][j] = sprites['withkey']
    #         if (sprite,) in astate.state['is_monster']:
    #             data[i][j] = sprites['monsterQuick']
    #         if (sprite,) in astate.state['is_key']:
    #             data[i][j] = sprites['key']
    #         if (sprite,) in astate.state['is_door']:
    #             data[i][j] = sprites['goal']
            
    #     if 'wall' in astate.state.keys():
    #         for c in astate.state['wall']:
    #             cell = c[0]
    #             i = int(cell.replace('cell_','').split('_')[0])
    #             j = int(cell.replace('cell_','').split('_')[1])
    #             data[i][j] = sprites['wall']
    #     return data.T
      
    def plot_state(self,zstate):
        sprites = {
                "goal": 'g', 
                "key": '+',         
                "nokey": 'A', 
                "monsterQuick": '1', 
                "monsterNormal": '2', 
                "monsterSlow": '3', 
                "wall":"w",
                "floor":".",
                "withkey":"Q"
            }
        x_axis_size = zstate.grid_height
        y_axis_size = zstate.grid_width
        data = np.chararray([y_axis_size,x_axis_size],unicode=True)
        try:
            for i in range(y_axis_size):
                for j in range(x_axis_size):
                    cell = 'cell_'+str(i)+'_'+str(j)
                    if (cell,) in zstate.state['wall']:
                        data[i,j] = sprites["wall"]
                    elif cell in zstate.state["door"]:
                        data[i,j] = sprites["goal"]
                    elif cell in zstate.state["key"]:
                        data[i,j]= sprites["key"]
                    elif cell in zstate.state["player"]:
                        if zstate.state["has_key"][0]==True:
                            data[i,j] = zstate.state["player_orientation"][0]#+sprites["withkey"]
                        else:
                            data[i,j] = zstate.state["player_orientation"][0]#+sprites["nokey"]
                    else:
                        data[i,j]='.'
            for pair in zstate.state["monster"]:
                x = int(pair[1].replace("cell_","").split('_')[0])
                y = int(pair[1].replace("cell_","").split('_')[1])
                data[x,y] = sprites["monsterQuick"]
            print(data.T)
        except KeyError:
            pass

    def update_high_actions(self,actions):
        #just to make sure this is called atleast once
        self.high_actions.update(actions)

    def generate_random_state(self,r=4,c=4,min_walls = 0,max_walls = None):
        random_state = Zelda_State()
        random_state.grid_height = r
        random_state.grid_width = c
        if max_walls == None:
            max_walls = int(5 * c * r / 10)

        while True:
            #try:
            random_state = Zelda_State()
            random_state.grid_height = r
            random_state.grid_width =  c
            #player_location = 'cell_'+str(np.random.randint(1,c-1))+'_'+str(np.random.randint(1,r-1))
            player_location = 'cell_'+str(np.random.randint(1,c))+'_'+str(np.random.randint(1,r))
            for i in range(c):
                for j in range(r):
                    cell_name = 'cell_'+str(i)+'_'+str(j)
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
            
            #num_monsters = np.random.randint(2,5)
            num_monsters = 1
            if max_walls!=0:
                num_blocked_cells = np.random.choice(range(min_walls,max_walls),replace = False)
            else:
                num_blocked_cells = 0
            all_cells = list(random_state.rev_objects.keys())

            #walls
            blocked_cells = np.random.choice(all_cells, num_blocked_cells,replace = False)
            all_cells = list(set(tuple(all_cells)).difference(set(tuple(blocked_cells))))
            #monster
            monster_positions = np.random.choice(all_cells, num_monsters,replace = False)
            all_cells = list(set(tuple(all_cells)).difference(set(tuple(monster_positions))))
            monster_mapping = {}
            for i in range(len(monster_positions)):
                monster_mapping[monster_positions[i].replace('cell','monster')] = monster_positions[i]
                random_state.rev_objects[monster_positions[i].replace('cell','monster')] = "monster"
            #door
            door_position = np.random.choice(all_cells,replace = False)
            random_state.rev_objects['door0']='door'
            all_cells.remove(door_position)
            #key
            key_position = np.random.choice(all_cells,replace = False)
            random_state.rev_objects['key0']='key'
            all_cells.remove(key_position)
            #player
            player_position = np.random.choice(all_cells,replace = False)
            random_state.rev_objects['player0']='player'
            all_cells.remove(player_position)
            #random_state.monster_mapping = monster_mapping 
            random_state.state['player_orientation'] =['EAST']
            [random_state.state['monster'].append((k,v)) for k,v in monster_mapping.items()]
            [random_state.state['wall'].append((blocked_cells[i],)) for i in range(len(blocked_cells))]
            
            [random_state.state['clear'].append(all_cells[i]) for i in range(len(all_cells))]
            random_state.state['clear'].append(door_position)
            
            random_state.state['player'].append(player_position)
            random_state.state['key'].append(key_position)
            random_state.state['door'].append(door_position)
            random_state.state['has_key'] = [False]
            random_state.state['escaped'] = [False]
            # ek = []
            # if abstract:
            #     for k,v in random_state.state.items():
            #         if len(v)==0:
            #             ek.append(k)
            #     for k in ek:
            #         del random_state.state[k]
            random_state.objects = invert_dictionary(random_state.rev_objects)
            if self.validate_state(self.abstract_state(random_state)):
                break
            else:
                print("still generating")
                self.validate_state(self.abstract_state(random_state))
            
        return random_state
   
    def get_next_state(self,state,action):
        '''
            given state and action, apply action virtually and get resulting state
            actions: up,down,right,left,use
            input: ZeldaState, Action name
            assume only legal actions applied, including no effect
        '''
        try:
            current_position = state.state['player'][0]
            x = int(current_position.replace('cell_','').split('_')[0])
            y = int(current_position.replace('cell_','').split('_')[-1])
            current_orientation = state.state['player_orientation'][0]
            #assume cell naming convention to avoid searching
            cell_up = 'cell_'+str(x)+'_'+str(y-1)
            cell_down = 'cell_'+str(x)+'_'+str(y+1)
            cell_right = 'cell_'+str(x+1)+'_'+str(y)
            cell_left = 'cell_'+str(x-1)+'_'+str(y)
            monster_locs = []
            for pair in state.state['monster']:
                monster_locs.append(pair[1])
            if cell_up not in state.rev_objects.keys() or (cell_up,) in state.state['wall'] or (cell_up,current_position) not in state.state['above']:
                cell_up = None
            if cell_down not in state.rev_objects.keys() or (cell_down,) in state.state['wall'] or (cell_down,current_position) not in state.state['below']:
                cell_down = None    
            if cell_right not in state.rev_objects.keys() or (cell_right,) in state.state['wall'] or (cell_right,current_position) not in state.state['rightOf']:
                cell_right = None    
            if cell_left not in state.rev_objects.keys() or (cell_left,) in state.state['wall'] or (cell_left,current_position) not in state.state['leftOf']:
                cell_left = None    
            d = {
                'EAST': cell_right,
                'WEST': cell_left,
                'NORTH': cell_up,
                'SOUTH': cell_down
            }
            facing_cell = d[current_orientation] #cell the player is facing
            keys = state.state['key']
            doors = state.state['door']
        except KeyError as e:
            print("Something wrong with state!")
        '''
            arrow effects: if facing in same direction, move else change orientation of player
            upon moving, if all monsters  killed and next cell is door, then escape
            upon moving, if next cell is key, then obtain key
            use effects: if monster present in facing cell, then kill monster. otherwise no effect
        '''
        next_state = copy.deepcopy(state)
        if action == 'ACTION_UP':
            if cell_up !=None and facing_cell == cell_up and cell_up not in monster_locs:
                next_state.state['clear'].append(current_position)
                if cell_up in next_state.state['clear']:
                    next_state.state['clear'].remove(cell_up)
                
                next_state.state['player'] = [cell_up]                
                current_position = cell_up
            else:
                next_state.state['player_orientation'] = ['NORTH']
                return next_state                
        if action == 'ACTION_DOWN':
            if cell_down !=None and facing_cell == cell_down and cell_down not in monster_locs:
                next_state.state['clear'].append(current_position)
                if cell_down in next_state.state['clear']:
                    next_state.state['clear'].remove(cell_down)
                
                next_state.state['player'] = [cell_down]
                current_position = cell_down
            else:
                next_state.state['player_orientation'] = ['SOUTH']
                return next_state
        if action == 'ACTION_RIGHT':
            if cell_right!=None and facing_cell == cell_right and cell_right not in monster_locs:
                next_state.state['clear'].append(current_position)
                if cell_right in next_state.state['clear']:
                    next_state.state['clear'].remove(cell_right)
                
                next_state.state['player'] = [cell_right]
                current_position = cell_right
            else:
                next_state.state['player_orientation'] = ['EAST']
                return next_state
        if action == 'ACTION_LEFT':
            if cell_left!=None and facing_cell == cell_left and cell_left not in monster_locs:
                next_state.state['clear'].append(current_position)
                if cell_left in next_state.state['clear']:
                    next_state.state['clear'].remove(cell_left)
                
                next_state.state['player'] = [cell_left]
                current_position = cell_left
            else:
                next_state.state['player_orientation'] = ['WEST']
                return next_state
        if action == 'ACTION_USE':
            if facing_cell in monster_locs:
                for i,pair in enumerate(state.state['monster']):
                    if pair[1] == facing_cell:
                        next_state.state['clear'].append(facing_cell)
                        del next_state.state['monster'][i]
                        break
            else:
                return state
        
        if current_position in keys:
            next_state.state['key'].remove(current_position)
            next_state.state['has_key'] = [True]

        if current_position in doors and len(state.state['monster'])==0 and state.state['has_key'][0]==True:
            next_state.state['escaped'] = [True]
        if len(next_state.state['player']) == 0 or next_state.state['player'] == None:
            print("WTF Player")
        return next_state

    def get_successor(self,state):
        action_dict = {
        'ACTION_UP':[],
        'ACTION_DOWN':[],
        'ACTION_RIGHT':[],
        'ACTION_LEFT':[],
        'ACTION_USE':[],
        }
        for action in action_dict:
            next_state = self.get_next_state(state,action)
            if next_state == state:
                action_dict[action] = [0,state]
            else:
                action_dict[action] = [1,next_state]
        return action_dict
    
    def is_goal_state(self,current_state,goal_state):
        #all orientations should be corrent goal state
        dcurrent_state = copy.deepcopy(current_state)
        dcurrent_state.state['player_orientation'] = None
        dgoal_state = copy.deepcopy(goal_state)
        dgoal_state.state['player_orientation'] = None
        if dcurrent_state==dgoal_state:
            return True
        else:
            return False

    @saved_plan
    def plan_to_state(self,state1,state2,algo="custom-astar",full_trace = False):
        '''
        orientation is not considered for goal check, this is done since
        we need to plan only to abstract states which do not differ by orientation
        '''
        state1_ = copy.deepcopy(state1)
        state2_ = copy.deepcopy(state2)
        action_dict = self.get_successor(state1_)
        print("Planning")
        if algo == "human":
            actions = {
            'w':'ACTION_UP',
            'a':'ACTION_LEFT',
            's':'ACTION_DOWN',
            'd':'ACTION_RIGHT',
            'e':'ACTION_USE'
            }
            action_list = []
            total_nodes_expanded = 0
            print("Solve this muggle:")
            print(self.plot_state(state1_))
            print(self.plot_state(state2_))
            print("=========")
            while(True):
                print(self.plot_state(state1_))
                action = actions.get(input())
                if action==None:
                    continue
                else:
                    action_list.append(action)
                temp = self.get_next_state(state1_,action)
                compare_dict(temp.state,state1_.state)
                state1_ = temp
                if not self.validate_state(self.abstract_state(state1_)):
                        print("WWWTTTTFFF!")
                        x = self.abstract_state(state1_)
                        self.validate_state(x)
                if state1_==state2_:
                    break
            
            action_dict = self.get_successor(state1_)
        else:
            action_list,total_nodes_expanded = search(state1_,state2_,self,algo)
        return action_list,total_nodes_expanded
        #print(plot_state(state2))
        #print("Plan:"+str(action_list))

    def execute_from_ID(self,abs_state,abs_action):
        try:
            abs_before,abs_after = self.high_actions[abs_action]
            #checking if just state equality is enough
            #if abs_before.state == abs_state.state and abs_before.rev_objects == abs_state.objects:
            #if abs_before!=abs_state: #Might have to change this to a more sophisticated comparison
            if abs_before.state == abs_state.state:
                return True,abs_after
            else:
                return False,abs_state
        except KeyError:
            print("Unknown Action ID!")

    def validate_state(self,ostate):
        '''
            Given ABSTRACT STATE, validate it
            assuming cell positioning is correct already, those are not to be learnt anyway
        '''
        state = copy.deepcopy(ostate.state)
        rev_objs = copy.deepcopy(ostate.rev_objects)
        player_loc = None
        key_loc = None
        door_loc = None
        monster_loc = None
        occupied_cells = []
        
        necessary_keys = ['leftOf','rightOf','above','below']
        if len(set(tuple(necessary_keys)).difference(tuple(state.keys())))>0:
            return False

        for k,values in state.items():
            if 'at' in k:
                for v in values:
                    if v[0] == 'player0':
                        if player_loc!=None:
                            return False
                        player_loc = v[1]
                        occupied_cells.append(v[1])
                    elif v[0] == 'key0':
                        key_loc = v[1]
                        occupied_cells.append(v[1])
                    elif v[0] == 'door0':
                        door_loc = v[1]
                    else:
                        monster_loc = v[1]
                        occupied_cells.append(v[1])

        if state.get('wall')!=None:
            for v in state.get('wall'):
                occupied_cells.append(v[0])

        #at, wall, clear
        if len(occupied_cells)!=len(set(occupied_cells)):
            return False
        
        for k,v in rev_objs.items():
            if v == 'location':
                if state.get('clear')!=None:
                    if (k in occupied_cells and (k,) in state.get('clear')) or (k not in occupied_cells and (k,) not in state.get('clear')):
                        return False

        if player_loc!=None:
            #at player, is_player, next_to_monster
            player_x = int(player_loc.replace('cell_','').split('_')[0])
            player_y = int(player_loc.replace('cell_','').split('_')[1])
            if monster_loc!=None:
                monster_x = int(monster_loc.replace('cell_','').split('_')[0])
                monster_y = int(monster_loc.replace('cell_','').split('_')[1])
                if (abs(monster_x-player_x) + abs(monster_y-player_y) == 1) and state.get('next_to_monster') == None:
                    return False
            else:
                if state.get('next_to_monster')!=None:
                    return False
        else:
            if state.get('next_to_monster')!=None:
                    return False

        if key_loc!=None:
            #at key, is_key, has_key
            if state.get('has_key')!=None:
                return False
        
        if door_loc == None:
            if state.get('escaped')!=None:
                return False

        if monster_loc!= None:
            #at monster, is_monster, monster_alive, next_to_monster
            monster_x = int(monster_loc.replace('cell_','').split('_')[0])
            monster_y = int(monster_loc.replace('cell_','').split('_')[1])
            monster_name = 'monster_'+str(monster_x)+'_'+str(monster_y)
            if state.get('monster_alive')!=[(monster_name,)]:
                return False
            if state.get('next_to_monster')!=None:
                if player_loc!=None:
                    player_x = int(player_loc.replace('cell_','').split('_')[0])
                    player_y = int(player_loc.replace('cell_','').split('_')[1])
                    if(abs(monster_x-player_x) + abs(monster_y-player_y) != 1):
                        return False
                else:
                    return False
        else:
            if state.get('monster_alive')!=None:
                return False
            if state.get('next_to_monster')!=None:
                return False       
        
        if state.get('escaped')!=None:
            if state.get('monster_alive')!=None or state.get('has_key')==None or (player_loc!=door_loc and player_loc!=None):
                return False    
        else:
            if (door_loc == player_loc) and (door_loc!=None) and state.get('has_key')!=None and monster_loc == None:
                return False
        return True    
          
    def abstract_state(self,low_state):
        unary_predicates = ['has_key','escaped','monster_alive','next_to_monster']
        abs_state = AbstractZeldaState()
        #abs_state.state = defaultdict(list)
        abs_state.rev_objects = low_state.rev_objects
        # for obj in low_state.rev_objects:
        #     if low_state.rev_objects[obj] in ['location']:
        #         abs_state.rev_objects[obj]=low_state.rev_objects[obj]
        #     elif low_state.rev_objects[obj] == 'key':
        #         abs_state.rev_objects[obj] = "sprite"
        #         abs_state.state['is_key'].append((obj,))
        #     elif low_state.rev_objects[obj] == 'player':
        #         abs_state.rev_objects[obj] = "sprite"
        #         abs_state.state['is_player'].append((obj,))
        #     elif low_state.rev_objects[obj] == 'door':
        #         abs_state.rev_objects[obj] = "sprite"
        #         abs_state.state['is_door'].append((obj,))
        #     elif low_state.rev_objects[obj] == 'monster':
        #         abs_state.rev_objects[obj] = "sprite"
        #         abs_state.state['is_monster'].append((obj,))
            
        abs_state.state['leftOf'] = low_state.state['leftOf']
        abs_state.state['rightOf'] = low_state.state['rightOf']
        abs_state.state['above'] = low_state.state['above']
        abs_state.state['below'] = low_state.state['below']
        abs_state.state['wall'] = low_state.state['wall']
        try:
            abs_state.state['at_0'].append(('player0',low_state.state['player'][0]))
            # abs_state.rev_objects['player0']='sprite'
            #abs_state.state['is_player'].append(('player0',))
        except IndexError:
            # if len(low_state.state['sword'])==1: #REMOVE DEPENDENCY ON SWORD!
            #     #print("No player in low level state, but sword is there")
            #     abs_state.state['at'].append(('player',low_state.state['sword'][0]))
            # else:
            print("No player, no sword. this is foul play")
            pass
        try:
            #abs_state.state['at'].append(('key',low_state.state['key']))#assuming there's just one
            #abs_state.state['is_key'].append('key')
            for i,val in enumerate(low_state.state['key']):
                # abs_state.rev_objects['key'+str(i)]='sprite'
                #abs_state.state['is_key'].append(('key0',))
                abs_state.state['at_1'].append(('key'+str(i),val))
        except IndexError:
            print("No key in low level state")
            pass
        for pair in low_state.state['monster']:
            x = int(pair[1].replace('cell_','').split('_')[0])
            y = int(pair[1].replace('cell_','').split('_')[1])
            cell_up = 'cell_'+str(x)+'_'+str(y-1)
            cell_down = 'cell_'+str(x)+'_'+str(y+1)
            cell_right = 'cell_'+str(x+1)+'_'+str(y)
            cell_left = 'cell_'+str(x-1)+'_'+str(y)
            for cell in [cell_up,cell_down,cell_right,cell_left]:
                if ('player0',cell) in abs_state.state['at_0']:
                    abs_state.state['next_to_monster'] = [()]
            abs_state.state['at_2'].append((pair[0],pair[1]))
            abs_state.state['monster_alive'].append((pair[0],))
            #abs_state.state['is_monster'].append((pair[0],))
            # abs_state.rev_objects[pair[0]]='sprite'
        try:
            for i,val in enumerate(low_state.state['door']):
                #abs_state.rev_objects['door'+str(i)]='sprite'
                #abs_state.state['is_door'].append(('door'+str(i),))
                abs_state.state['at_3'].append(('door'+str(i),val))
        except IndexError:
            print("No door in low level state WHAT?!")
            pass
        try:
            if low_state.state['has_key'][0]:
                abs_state.state['has_key'] = [()]
        except IndexError:
            print("No has_key in low level state")
            pass
        
        if low_state.state['escaped'][0]:
            abs_state.state['escaped'] = [()]             
        
        for cell in low_state.state['clear']:
            abs_state.state['clear'].append((cell,))

        abs_state.grid_height = low_state.grid_height 
        abs_state.grid_width = low_state.grid_width
        ek = []
        for k,v in abs_state.state.items():
            if v != None:
                if len(v)==0:
                    ek.append(k)
                    # if k not in unary_predicates:
                    #     print("WTF"+str(k))
            else:
                ek.append(k)
        [abs_state.state.pop(k) for k in ek]
        # if len(abs_state.state['is_player'])>1:
        #     print("WTFWTF")
        #abs_state.objects = invert_dictionary(abs_state.rev_objects)
        return abs_state

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
        
    def refine_abstract_state(self,abstract_state_):
        '''
            Concretize an input abstract state
        '''
        abstract_state = copy.deepcopy(abstract_state_)
        all_keys = ['at_0','at_1','at_2','at_3','monster_alive','has_key','escaped','wall','leftOf','rightOf','above','below']
        refined_state = Zelda_State()        
        # for obj in abstract_state.rev_objects:
        #     if abstract_state.rev_objects[obj] in ['location']:
        #         refined_state.rev_objects[obj]=abstract_state.rev_objects[obj]
        
        refined_state.rev_objects = abstract_state.rev_objects
        refined_state.state['wall'] = abstract_state.state.get('wall')
        refined_state.state['leftOf'] = abstract_state.state.get('leftOf')
        refined_state.state['rightOf'] = abstract_state.state.get('rightOf')
        refined_state.state['above'] = abstract_state.state.get('above')
        refined_state.state['below'] = abstract_state.state.get('below')
        refined_state.state['player_orientation'].append('NORTH')
        
        if abstract_state.state['escaped'] == None:
            refined_state.state['escaped'] = [False]
        else:
            refined_state.state['escaped'] = [True]
        
        if abstract_state.state['has_key'] == None:
            refined_state.state['has_key'] = [False]
        else:
            refined_state.state['has_key'] = [True]

        if abstract_state.state.get('at_0')!=None:
            for pair in abstract_state.state['at_0']:
                refined_state.state['player'].append(pair[1])
                #refined_state.rev_objects[pair[0]]='sprite'
        if abstract_state.state.get('at_1')!=None:
            for pair in abstract_state.state['at_1']:
                refined_state.state['key'].append(pair[1])
                #refined_state.rev_objects[pair[0]]='sprite'
        if abstract_state.state.get('at_3')!=None:
            for pair in abstract_state.state['at_3']:
                refined_state.state['door'].append(pair[1])
                #refined_state.rev_objects[pair[0]]='sprite'
        if abstract_state.state.get('at_2')!=None:
            for pair in abstract_state.state['at_2']:
                refined_state.state["monster"].append((pair[0],pair[1]))
                #refined_state.rev_objects[pair[0]]='sprite'
        
        if abstract_state.state['clear']!=None:
            for cell in abstract_state.state['clear']:
                refined_state.state['clear'].append(cell[0])

        refined_state.grid_height = abstract_state.grid_height
        refined_state.grid_width = abstract_state.grid_width
        for k,v in refined_state.state.items():
            if(v) == None:
                print(str(k)+" is empty")
                refined_state.state[k] = []
        refined_state.objects = invert_dictionary(refined_state.rev_objects)
        return refined_state

    def get_relational_state(self,state):
        rstate = AbstractZeldaState()
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
                            rstate.grid_width = max(rstate.grid_width,x)
                        else:
                            rstate.rev_objects[_p] = _p[:-1]
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
   
    def get_ground_state(self,state):
        gstate = AbstractZeldaState()
        gstate.state = {}
        for k,v in state.state.items():
            if v!=None:
                p = k
                for _v in v:
                    gstate.state[k+"-"+"-".join(list(_v))]=[()]
        gstate.objects = {}
        gstate.rev_objects = {}
        return gstate
    
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

class ZeldaGVGAgent():
    def __init__(self,r,c,min_walls=0,ground_actions = False):
        self.ground_actions = ground_actions
        
        files_dir = "../gvg_agents/files/zelda/"+str(r)+'_'+str(c)+"/"
        if not os.path.isdir(files_dir):
            os.mkdir(files_dir)
        self.translator = Zelda_Translator(ground_actions= ground_actions,files_dir=files_dir)
        #files_dir = "/home/raoshashank/agent_interrogation/GVGAI-master/clients/GVGAI-PythonClient/src/files/"
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
        self.r = r
        self.c = c
        self.query_history_file = files_dir + "zelda_queries"
        self.queries = {}
        self.saved_correct_states = {}
        self.saved_correct_states_file = files_dir+"saved_correct_states"
        try:
            with open(self.query_history_file,"rb") as f:
                self.queries = pickle.load(f)
        except IOError:
            print("No old queries to load")

        try :
            with open(self.random_states_file,"rb") as f:
                temp_states = pickle.load(f)  
        except IOError:
            temp_states = self.generate_random_states(n = num_random_states,r=r,c=c,min_walls=min_walls,algo = "human",abstract = True,random = True, save_trace = True)
        ###generate additional states for data
        n_extra = 0
        self.load_actions()
        self.combine_actions()
        temp_states_extra = self.generate_random_states(n = n_extra, r = r,c = c,min_walls=min_walls,add_intermediate=True,abstract = True,random = True, save_trace = False)
        self.show_actions()
        with open(files_dir+"temp_states_extra","wb") as f:
            pickle.dump(temp_states_extra,f)
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
    
    # @saved_state
    # def get_correct_state(self,fixed_preds,state):
    #     random_state = AbstractZeldaState()
    #     random_state.grid_height = c = self.grid_size 
    #     random_state.grid_width = r =  self.grid_size 
    #     for i in range(c):
    #         for j in range(r):
    #             cell_name = 'cell_'+str(i)+'_'+str(j)
    #             cell_up = 'cell_'+str(i)+'_'+str(j-1)
    #             cell_down = 'cell_'+str(i)+'_'+str(j+1)
    #             cell_right = 'cell_'+str(i+1)+'_'+str(j)
    #             cell_left = 'cell_'+str(i-1)+'_'+str(j)
    #             random_state.rev_objects[cell_name] = 'location'
    #             random_state.state['clear'].append((cell_name,))
    #             if i+1<c:
    #                 if (cell_name,cell_right) not in random_state.state['leftOf']:
    #                     random_state.state['leftOf'].append((cell_name,cell_right))
    #                 if (cell_right,cell_name) not in random_state.state['rightOf']:
    #                     random_state.state['rightOf'].append((cell_right,cell_name))
                
    #             if i!=0:
    #                 if (cell_left,cell_name) not in random_state.state['leftOf']:
    #                     random_state.state['leftOf'].append((cell_left,cell_name))
    #                 if (cell_name,cell_left) not in random_state.state['rightOf']:
    #                     random_state.state['rightOf'].append((cell_name,cell_left))

    #             if j+1<r:
    #                 if (cell_name,cell_down) not in random_state.state['above']:
    #                     random_state.state['above'].append((cell_name,cell_down))
    #                 if (cell_down,cell_name) not in random_state.state['below']:
    #                     random_state.state['below'].append((cell_down,cell_name))
            
    #             if j!=0:
    #                 if (cell_up,cell_name) not in random_state.state['above']:
    #                     random_state.state['above'].append((cell_up,cell_name))
    #                 if (cell_name,cell_up) not in random_state.state['below']:
    #                     random_state.state['below'].append((cell_name,cell_up))    
    #     random_state.state['is_player'] = [('player0',)]
    #     random_state.rev_objects['player0'] = 'sprite'
    #     random_state.state['is_key'] = [('key0',)]
    #     random_state.rev_objects['key0'] = 'sprite'
    #     #random_state.state['is_monster']= [('monster0',)]
    #     for k,v in state.items():
    #         if 'is_monster' in k:
    #             random_state.state['is_monster'] = [(k.split('-')[1],)]
    #             random_state.rev_objects[k.split('-')[1]] = 'sprite'
    #             break
    #     assert 'is_monster' in random_state.state
        
    #     random_state.state['is_door']=[('door0',)]
    #     random_state.rev_objects['door0'] = 'sprite'
    #     domain_file = "../gvg_agents/files/state_fixer/zelda_domain.pddl"
    #     problem_file = "../gvg_agents/files/state_fixer/zelda_problem.pddl"
    #     result_file = "../gvg_agents/files/state_fixer/zelda_result.txt"
    #     problem_text = "(define (problem zelda)\n    (:domain zelda)\n   (:objects\n       "

    #     for obj,typ in random_state.rev_objects.items():
    #         problem_text+=str(obj)+" - "+str(typ)+"\n       "
    #     problem_text+="    )\n    (:init\n          "

    #     for pred,values in random_state.state.items():
    #         for v in values:
    #             problem_text+="("+str(pred)+" "+" ".join(list(v))+")\n          "
        
    #     problem_text+=")\n    (:goal (and\n          "


    #     goal_condition ="(and \n\
    #             (exists \n\
    #                 (?loc1 - location ?loc2 - location)\n\
    #                 (and \n\
    #                     (at player0 ?loc1) \n\
    #                     (at door0 ?loc2)\n\
    #                 )\n\
    #             )   \n\
    #             (or\n\
    #                 (has_key )\n\
    #                 (exists \n\
    #                     (?loc2 - location)\n\
    #                     (at key0 ?loc2)\n\
    #                 \n\
    #                 )\n\
    #             )\n"
    #     for pred in fixed_preds:
    #         p = pred.split('-')[0]
    #         args = pred.split('-')[1:]
    #         goal_condition+="                (not ("+p+" "+ " ".join(args)+"))\n          "+")"
        
    #     goal_condition+="            )\n   )\n)"
        
    #     with open(problem_file,'w') as f:
    #         f.write(problem_text)
    #         f.write(goal_condition)
    #     print("Wrote problem file")
    #     plan = call_planner(domain_file,problem_file,result_file)
    #     print(plan)
    #     if len(plan) != 0:
    #         action_parameters, predTypeMapping, agent_model, abstract_model, objects, reverse_types, init_state, _ = generate_ds(domain_file,problem_file)
    #         _plan = ExecuteSimplePlan(agent_model, random_state.state,plan)
    #         _,set_final_state, _ = _plan.execute_plan()
    #         grounded_final_state = State({},{})
    #         for k in set_final_state:
    #             if 'assigned' in k:
    #                 continue
    #             if 'at-' in k.split('|')[0]:
    #                 k = k.replace(k.split('|')[0],'at') 
    #             grounded_final_state.state[k.replace('|','-')]=[()]
    #         rstate = self.get_relational_state(grounded_final_state)
    #         assert self.validate_state(rstate) == True
    #         return grounded_final_state            
    #     else:
    #         print("failed to plan")
    #         return False

    def fix_state(self,fixed_preds,state,removed,predTypeMapping):
        fstate = copy.deepcopy(state)
        preds_added = {}
        if removed:
            #fixing when preds are removed
            for pred,v in fixed_preds.items():

                # if len(v) == 1:
                #     del fstate[pred]
                #     assert (pred not in list(fstate.keys()))
                # else:
                #     fstate[pred].remove(v)

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
                    #temporary fix
                    if 'monster' in args[0]:
                        del fstate['monster_alive-'+args[0]]
                    if 'next_to_monster-' in fstate and args[0]=='player0':
                        del fstate['next_to_monster-']
                        #find cells next to monster
                        # for k,v in state:
                        #     if 'at' in k and 'monster' in k:
                        #         monster_loc = k.split('-')[-1]
                        #         x = int(monster_loc.split('_')[0])
                        #         y = int(monster_loc.split('_')[1])
                        #         up = 'cell_'+str(x)+str(y-1)
                        #         right = 'cell_'+

                    fstate['clear-'+str(args[1])]=[()]
                    preds_added['clear-'+str(args[1])] = [()]  
            #assert self.validate_state(fstate)
        else:
            #fixing when preds are added
            cell_mapping = defaultdict(list)
            tp = ['at_0','at_1','at_2','at_3','clear','wall']
            player_loc = None
            for p in fstate: 
                pname = p.split('-')[0]
                args = p.split('-')[1:]
                if pname in tp:
                    if 'at' in pname:
                        if pname == 'at_0':
                            player_loc = args[1]
                        cell_mapping[args[1]].append(p)
                    else:
                        cell_mapping[args[0]].append(p)
                    
            for pred in [fixed_preds]:
                pname = pred.split('-')[0]
                args = pred.split('-')[1:]
                if pname == 'clear':
                    #added clear, so remove anything that is in that location 
                    for item in cell_mapping[args[0]]:
                        if 'door' not in item:
                            fstate.remove(item) 
                            if 'monster' in item:
                                if 'next_to_monster-' in fstate:
                                    fstate.remove('next_to_monster-')
                    #fstate.remove['wall-'+str(args[0])] = [()]
                    #preds_added['wall-'+str(args[0])] = [()]
                if pname == 'wall':
                    #add wall, so remove clear and anything else in that location
                    for item in cell_mapping[args[0]]:
                        fstate.remove(item) 
                        if 'monster' in item:
                            if 'next_to_monster-' in fstate:
                                fstate.remove('next_to_monster-')
                    #fstate['clear-'+str(args[0])] = [()]
                    #preds_added['clear-'+str(args[0])] = [()]    
                if 'at' in pname:
                    #temporary fix
                    #added at something so remove wall or clear or anything else in that 
                    #location
                    for item in cell_mapping[args[1]]:
                        if not ('door' in pred and 'clear' in item):
                            fstate.remove(item) 
                    if 'door' in args[0]:
                        fstate.add('clear-'+args[1])

                    ###add next to monster check

                    if 'key' in args[0]:
                        if 'has_key-' in fstate:
                            fstate.remove('has_key-')
                        

                    if 'monster' in args[0]:
                        fstate.add('monster_alive-'+args[0])
                    
                        if 'leftOf-'+player_loc+'-'+args[1] in fstate or 'above-'+player_loc+'-'+args[1] in fstate or 'below-'+player_loc+'-'+args[1] in fstate or 'rightOf-'+player_loc+'-'+args[1] in fstate: 
                            fstate.add('next_to_monster-')
                    '''
                    if 'next_to_monster-' in fstate and args[0]=='player0':
                        del fstate['next_to_monster-']
                        #find cells next to monster
                        # for k,v in state:
                        #     if 'at' in k and 'monster' in k:
                        #         monster_loc = k.split('-')[-1]
                        #         x = int(monster_loc.split('_')[0])
                        #         y = int(monster_loc.split('_')[1])
                        #         up = 'cell_'+str(x)+str(y-1)
                        #         right = 'cell_'+
                    '''

                    #fstate['clear-'+str(args[1])]=[()]
                    #preds_added['clear-'+str(args[1])] = [()]

                if 'alive' in pname:
                    for item in cell_mapping['cell_'+pred.replace('monster_alive-monster_','')]:
                        if not ('door' in pred and 'clear' in item):
                            fstate.remove(item) 
                    fstate.add('at_2-'+pred.replace('monster_alive-','')+'-'+'cell_'+pred.replace('monster_alive-monster_',''))
                    a = 'cell_'+pred.replace('monster_alive-monster_','')
                    if 'leftOf-'+player_loc+'-'+a in fstate or 'above-'+player_loc+'-'+a in fstate or 'below-'+player_loc+'-'+a in fstate or 'rightOf-'+player_loc+'-'+a in fstate:
                            fstate.add('next_to_monster-')
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
        # if self.queries.get(qkey):
        #     result = self.queries[qkey]
        #     return result[0],result[1],result[2] 

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
                                    print("add effect already in state!")
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
                                    print("delete effect already in state!")
                                    return False,i-1,self.translator.get_ground_state(state)
                                else:
                                    #apply del effect
                                    state.state[pred].remove(val)
                                    if len(state.state[pred]) == 0:
                                        temp.append(pred)
                        else:
                            print("delete effect not in state!")
                            return False,i-1,self.translator.get_ground_state(state)
                    [state.state.pop(k_,None) for k_ in temp]
                    
                    #action effects applied, now check if we can plan to this state if its valid
                    test = False
                    if test:
                        actions,total_nodes_expanded = self.translator.plan_to_state(self.translator.refine_abstract_state(previous_state),self.translator.refine_abstract_state(state),'human')
                    if self.translator.validate_state(state):
                        try:
                            actions,total_nodes_expanded = func_timeout(10,self.translator.plan_to_state,args = (self.translator.refine_abstract_state(previous_state),self.translator.refine_abstract_state(state),'custom-astar'))
                        except FunctionTimedOut:
                            actions,total_nodes_expanded = self.translator.plan_to_state(self.translator.refine_abstract_state(previous_state),self.translator.refine_abstract_state(state),'human')
                        if actions == None:
                            print("Sim Can't plan between States!")
                            return False,i-1,self.translator.get_ground_state(state)
                        else:
                            previous_state = copy.deepcopy(state)
                    else:
                        print("Invalid modified state!")
                        return False,i,self.translator.get_ground_state(state)
                    i+=1
                return True,i,self.translator.get_ground_state(state)
            else:
                return False, -1, self.translator.get_ground_state(state)
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

    def solve_game(self,state,_actions=False,algo = 'custom-astar'):
        states = []
        final_state = self.get_solved_state(state)
        actions = {
        'w':'ACTION_UP',
        'a':'ACTION_LEFT',
        's':'ACTION_DOWN',
        'd':'ACTION_RIGHT',
        'e':'ACTION_USE'
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
        temp_state = copy.deepcopy(state)
        temp_state.state['clear'].append(temp_state.state['monster'][0][1])
        temp_state.state['clear'].append(temp_state.state['key'][0])
        temp_state.state['clear'].append(temp_state.state['player'][0])
        temp_state.state['clear'].remove(temp_state.state['door'][0])
            
        temp_state.state['escaped'] = [True]
        temp_state.state['has_key'] = [True]
        temp_state.state['monster'] = []
        temp_state.state['player'] = temp_state.state['door']
        temp_state.state['key'] = []
        #print(self.plot_state(state))
        return temp_state

    def get_random_trace(self,state):
        max_len = 50
        trace  = []
        for _ in range(max_len):
            succ = self.translator.get_successor(state)
            choice = random.choice(list(succ.keys()))
            if state.state['escaped'][0]:
                trace.append((succ[choice][1],'ACTION_ESCAPE'))
                state = succ[choice][1]
                break
            else:
                trace.append((succ[choice][1],choice))
                state = succ[choice][1]
        return trace

    def generate_random_states(self,n=5,save=True,abstract = False,random = False,save_trace = False,r = 2,c = 2,min_walls = 0,add_intermediate=True,max_walls = None,algo = "custom_astar"):
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
        [initial_random_states.append(self.translator.generate_random_state(r = r,c = c,min_walls=min_walls,max_walls = max_walls)) for i in range(n)]
        if add_intermediate:
            abs_random_states = []
            solved_random_states = []
            num_random_traces = 0
            add_rs = []
            #get intermediate states
            for s in initial_random_states:
                # try:
                #     st,actions = func_timeout(10,self.solve_game,args = (s,_actions=True,algo='custom-astar'))
                # except FunctionTimedOut:
                st,actions = self.solve_game(s,_actions=True,algo='human')

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
                # if not isinstance(run[0][0],Zelda_State):
                #     zsa1 = self.translator.from_sso(sa1[0],objects)
                #     zsa2 = self.translator.from_sso(sa2[0],objects)
                # else:
                zsa1 = sa1[0]
                zsa2 = sa2[0]
                #if zsa1.state['has_key'][0] != zsa2.state['has_key'][0]:
                #    print("Here")
                sas_trace.append([zsa1,sa1[1],zsa2])
                if sa2[1]=='ACTION_ESCAPE':
                    break
                #if i == 7 and j>20:
                #    print(plot_state(zsa1))
                #    print("----"+str(i)+"--"+str(j))
                #    print(plot_state(zsa2))
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
        #return high_level_actions,high_level_traces 
               
    def combine_actions(self):
        if len(self.translator.high_actions)==0:
            print("Actions dict not saved yet!")
            return False
        self.actions = {}
        self.translator.high_actions['a0'] == self.translator.high_actions['a2']
        self.action_objects = {}
        for action,s in self.translator.high_actions.items():
            temp_action = Action(action,s[0],s[1])
            temp_action.assign_predicate_types()
            if temp_action not in self.action_objects.values():
                self.actions[action] = s
                self.action_objects[action] = temp_action
                #self.actions[-1].assign_predicate_types()
            else:
                print("Pruned!")
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

        # action_headers = defaultdict(list)
        # for action in self.actions:       
        #     action_headers[action.header].append(action)
        # for header,_actions in action_headers.items():
        #     print(str(header)+":"+str(len(_actions)))
        #     num_deleted = 0
        #     merged = {}
        #     checked = []
        #     for i,_a1 in enumerate(_actions):
        #             for j,_a2 in enumerate(_actions):
        #                     #if merged[i]!=j and merged[j]!=i and j not in merged.values():
        #                     if j not in checked:
        #                         if _a1 != _a2:
        #                             if _a1.modified_predicates_typed == _a2.modified_predicates_typed and _a1.static_relations_typed == _a2.static_relations_typed: #equal number of modified predicates
        #                                     if check_merge(_a1,_a2):
        #                                         #del action_headers[header][j]
        #                                         merged[j] = i #j is similar to i
        #                                         checked.extend([i,j])
                            
        #     unique_actions = set(range(0,len(_actions))).difference(set(merged.keys()))
        #     action_headers[header] = []
        #     [action_headers[header].append(_actions[u]) for u in unique_actions]
        #     print("Unique actions:")
        #     print(len(unique_actions))
        #     print("===========")
        #     for i,_a1 in enumerate(action_headers[header]):
        #         print("Added:")
        #         pp.pprint(_a1.added_predicates)
        #         print("Deleted:")
        #         pp.pprint(_a1.deleted_predicates)
        #         print("Static:")
        #         pp.pprint(_a1.relavant_static_props)
        #         print('\n')
        #         print("===========")
        # print("Number of actions trimmed:"+str(num_deleted))
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

'''
       (:action a5
  :parameters (              )
  :precondition (and (at_0-player0-cell_1_1)
        (at_1-key0-cell_2_1)
        (at_2-monster_2_2-cell_2_2)
        (monster_alive-monster_2_2)
       )
         :effect (and (not (at_0-player0-cell_1_1)
       )
        (not (at_1-key0-cell_2_1)
       )
        (next_to_monster-)
        (at_0-player0-cell_2_1)
        (clear-cell_1_1)
        (has_key-)
       ))

    (:action a4
    :parameters (              )
    :precondition (and (at_0-player0-cell_2_2)
        (at_3-door0-cell_2_1)
        (clear-cell_2_1)
        (has_key-)
        (not (at_2-monster_0_3-cell_0_3)
       )
        (not (at_1-key0-cell_1_2)
       )
        (not (monster_alive-monster_0_3)
       )
       )
         :effect (and (not (at_0-player0-cell_2_2)
       )
        (not (clear-cell_2_1)
       )
        (escaped-)
        (clear-cell_2_2)
        (at_0-player0-cell_2_1)
       ))


       )



'''
