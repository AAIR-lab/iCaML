from collections import defaultdict
import copy
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
        if self.state_before.state == action.state_before.state and self.state_after.state == action.state_after.state:
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

def returnNone():
    return None

class GVGAgent():
    def __init__(self,name):
        self.name = name
        return 

    def show_actions(self,action = None):
        if action!=None:
                v = self.translator.high_actions[action]
                print("------action_name:"+str(action)+"--------")
                print("State before: ")        
                print(self.translator.plot_abs_state(v[0]))
                print("State after: ")
                print(self.translator.plot_abs_state(v[1]))
        else:            
            for k,v in self.translator.high_actions.items():
                print("------action_name:"+str(k)+"--------")
                print("State before: ")        
                print(self.translator.plot_abs_state(v[0]))
                print("State after: ")
                print(self.translator.plot_abs_state(v[1]))
    
    def get_relational_state(self,state):
        if state in self.ground_to_relational_map:
            return self.ground_to_relational_map[state]
        else:
            rstate = self.translator.get_relational_state(state)
            self.ground_to_relational_map[state] = rstate
            return rstate
    
    def run_query(self,query):
        if len(self.translator.high_actions)!=0:
            #if 'next_to_monster-' in query['init_state'].state:
            #    print("This")
            #return self.translator.iaa_query(query['init_state'],query['plan'],self.action_objects)           
            state = copy.deepcopy(query['init_state'])
            previous_state = copy.deepcopy(state)
            i = 0
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
                    actions,total_nodes_expanded = self.translator.plan_to_state(self.translator.refine_abstract_state(previous_state),self.translator.refine_abstract_state(state))
                    if actions == None:
                        return False,i-1,self.translator.get_ground_state(state)
                    else:
                        previous_state = copy.deepcopy(state)
                else:
                    return False,i-1,self.translator.get_ground_state(state)
                i+=1
            return True,i,self.translator.get_ground_state(state)


        else:
            print("Actions not stored yet!")
            return False,-1,query['state']
    
    def get_more_random_states(self,n=10,save=False,random_walk=True):
        return_random = self.generate_random_states(n,abstract=True)
        self.random_states.extend(return_random)
        if save:
            with open(self.random_states_file,"rb") as f:
                temp_states = pickle.load(f)  
            temp_states.extend(return_random)
            with open(self.random_states_file,"wb") as f:
                pickle.dump(temp_states,f)  
        return return_random
    
    def validate_state(self,state):
        return self.translator.validate_state(state)
    
    def generate_ds(self):
        if len(self.translator.high_actions)!=0:
            return self.translator.generate_ds()
        else:
            #not created actions yet!
            print("Actions not stored yet")
            return False
    
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