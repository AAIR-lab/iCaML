#!/usr/local/bin/python3
# encoding: utf-8
        
import os
import glob
import pprint
import statistics
import time
from collections import OrderedDict
from agent import Agent
from config import *
from interrogation import AgentInterrogation
from lattice import Model
import pickle
from utils import *
from IPython import embed
from post_processing import *
import subprocess as sb
import xlwt
from xlwt import Workbook

def modify_types(types):
    new_types = {}
    if len(types.keys()) == 1 and list(types.keys())[0] == 'object':
        for o in types['object']:
            new_types[o] = []

    print(new_types)
    return new_types

def initialize_folders():
    try:
        os.stat("../temp_files")
    except OSError:
        os.mkdir("../temp_files")

    try:
        os.stat("../temp_files/results")
    except OSError:
        os.mkdir("../temp_files/results")

    try:
        os.stat("../domains")
    except OSError:
        print("ERROR: Domains directory missing")
        exit(-1)

    try:
        os.stat(FF_PATH + "ff")
    except OSError:
        print("ERROR: FF missing or not compiled")
        exit(-1)

    return

def view_results(abs_model,agent,file,domain,pred_type_mapping, action_parameters,grid):
    global sims_folder
    with open(file,"rb") as f:
        results = pickle.load(f)
    #print(results)
    output = ""
    valid_model = results[1]['valid_models'][0]
    action_objects = results[1]['agent_actions']
    #valid_model = remove_extra_preconds(valid_model,agent)
    
    for name,action in valid_model.actions.items():
        agent.agent_model.show_actions(name)
        add_preds = ""
        del_preds = ""
        for k,v in agent.agent_model.action_objects[name].added_predicates.items():
            for _v in v:
                add_preds+="("+k+"-"+"-".join(list(_v))+")\n"
        for k,v in agent.agent_model.action_objects[name].deleted_predicates.items():
            for _v in v:
                del_preds+="("+k+"-"+"-".join(list(_v))+")\n"
        output+="Predicates Added in trace action: "+'\n'
        if(add_preds == ""):
            output+="None"+'\n'
        else:
            output+=add_preds+'\n'
        output+="Preds Deleteded in trace action: "+'\n'
        if(del_preds == ""):
            output+="None"+'\n'
        else:
            output+=del_preds+'\n'
        output+="***Operator Learnt:****"+'\n'
        output+=":action "+name+" \n"+'\n'
        output+=":parameteres ()"+'\n'
        pre_pos = []
        pre_neg = []
        eff_add = []
        eff_del = []
        pre = "and(\n"
        eff = "and(\n"
        for pred in action:
            if pred not in abs_model.actions[name]:
                if action[pred][0] == Literal.POS:
                    pre_pos.append(pred)               
                if action[pred][0] == Literal.NEG:
                    pre_neg.append(pred)               
                if action[pred][1] == Literal.POS:
                    eff_add.append(pred)               
                if action[pred][1] == Literal.NEG:
                    eff_del.append(pred)               
        for lit in pre_pos:
            pre+="             ("+lit+")\n"
        for lit in pre_neg:
            pre+="\n              (not("+lit+"))\n"
        pre+=")\n"
        for lit in eff_add:
            eff+="             ("+lit+")\n"
        for lit in eff_del:
            eff+="\n              (not("+lit+"))\n"
        output+=":precondition "+'\n'
        output+=pre          +'\n'
        output+=":effect "   +'\n'
        output+=eff+'\n'
        output+=")"+'\n'
    output+="query_count:"+str(results[1]['query_count'])+'\n'
    output+="time:"+str(results[1]['time'])+'\n'
    output+="grid:"+str(results[1]['grid'])+'\n'
    output+="min_w:"+str(results[1]['min_w'])+'\n'
    output+="pal_tuple_count:"+str(results[1]['pal_tuple_count'])+'\n'
    with open(sims_folder+domain+'/'+str(grid[0])+'_'+str(grid[1])+'/output.txt','w') as f:
        f.write(output)
    
    domain_file ="../gvg_agents/files/"+domain+"/"+str(grid[0])+'_'+str(grid[1])+"/domain"+str(grid[0])+str(grid[1])+".pddl"
    problem_file = "../gvg_agents/files/"+domain+"/"+str(grid[0])+'_'+str(grid[1])+"/problem"+str(grid[0])+str(grid[1])+".pddl"
    result_file  = "../gvg_agents/files/"+domain+"/"+str(grid[0])+'_'+str(grid[1])+"/result"+str(grid[0])+str(grid[1])+".txt"
    with open(domain_file,"w") as f:
        write_model_to_file(valid_model,f,domain,pred_type_mapping,action_parameters)
    
    with open(agent.agent_model.high_traces,'rb') as f:
        ht = pickle.load(f)
    
    
    j=0
    init_state = agent.agent_model.translator.get_ground_state(ht[0][j][0])
    agent_model = agent.agent_model
    translator = agent_model.translator
    trace = ht[0]
    previous_state = None
    for state in trace:
        print("========")
        final_state = agent.agent_model.translator.get_ground_state(state[2])
        write_problem_to_file(problem_file,init_state.state,final_state.state,domain,pred_type_mapping,action_parameters)
        plan = call_planner(domain_file,problem_file,result_file)
        print(plan)
        if plan == []:
            can_apply_action(valid_model.actions['a3'],previous_state.state,final_state.state)
        else:
            previous_state = final_state
    
    return 

def main(domain,check_results,file,r,c,min_w,max_w):
    initialize_folders()
    i = 1
    results = {}
    results[i] = {}
    query_count_all = []
    running_time_all = []
    
    avg_trace_length_all = [] 
    num_traces_all = []

    data_dict_all = []
    pal_tuple_count_all = []
    agent = Agent(domain,{}, {},r,c,min_walls=min_w,max_walls = max_w,ground=ground_actions)
    
    action_parameters, pred_type_mapping, agent_model_actions, abstract_model_actions, \
    objects, old_types, init_state, domain_name = agent.agent_model.generate_ds()
    
    abstract_predicates = {}
    types = modify_types(old_types)

    pp = pprint.PrettyPrinter(indent=2)
    abstract_model = Model(abstract_predicates, abstract_model_actions) 
    
    #comment to include static predicates
    abs_preds_test, abs_actions_test, _ = agent.agent_model.bootstrap_model()
    abstract_model.predicates = abs_preds_test
    abstract_model.actions = abs_actions_test
    
    if not check_results:
        iaa_main = AgentInterrogation(agent, abstract_model, objects, domain_name,
                                        abstract_predicates, pred_type_mapping, action_parameters, types,load_old_q=True)
        
        query_count, running_time, data_dict, pal_tuple_count,valid_models = iaa_main.agent_interrogation_algo()
        agent.agent_model.show_actions( )
        
        query_count_all.append(query_count)
        running_time_all.append(running_time)
        data_dict_all.append(data_dict)
        pal_tuple_count_all.append(pal_tuple_count)
        print("Query Count: ", query_count) 
        print("Running Time: ", running_time)
        
        
        results[i]['query_count'] = query_count
        results[i]['time'] = running_time
        results[i]['avg_trace_length'] = agent.agent_model.avg_trace_length
        results[i]['grid'] = grid
        results[i]['min_w'] = min_w
        results[i]['pal_tuple_count'] = pal_tuple_count
        results[i]['data_dict'] = data_dict
        results[i]['valid_models'] = valid_models
        results[i]['agent_actions'] = agent.agent_model.action_objects


        with open(file,"wb") as f:
            pickle.dump(results,f)

        view_results(abstract_model,agent,file,domain,pred_type_mapping, action_parameters,grid)
        #time.sleep(1)
    else:
        
        view_results(abstract_model,agent,file,domain,pred_type_mapping, action_parameters,grid)
        

sims_folder = "../gvg_agents/files/"
if __name__ == "__main__":
    
    domains = {
        'zelda':[[3,4],
        [4,5],
        [5,6],
        [6,7],
        [8,8]],
        'cookmepasta':[[4,5],
        [5,6],
        [6,7],[8,8]],
        'escape':[[3,3],[4,4],[4,5],[6,7]],
        'snowman':[[4,5],[5,5],
        [5,6],
        [6,7],
        [8,8]]
        }
    grids = [
        [3,3],
        [4,4],
        [4,5],
        [5,6],
        [6,7],
        [8,8],
    ]
    domain = 'escape'
    wb = Workbook()
    for domain,grids in domains.items():
        rmfiles = "../gvg_agents/files/"+domain+"/"
        preds = []
        actions = []
        pal_tuples = []
        grid_size = []
        num_queries = []
        time = []
        sheet = wb.add_sheet(domain)
        for i,name in enumerate(['grid_size','preds','actions','pal_tuples','num_queries','time']):
             sheet.write(0,i+1,name)
        for i,grid in enumerate(grids):
            with open(rmfiles+'results/result'+str(grid[0])+'x'+str(grid[1]),'rb') as f:
                result = pickle.load(f)
            
            print('----------'+domain+'---'+str(grid)+'-----')
            # print('query_count = '+str(result[1]['query_count']))
            # print('pal_tuple_count = '+str(result[1]['pal_tuple_count']))
            # print('number of actions = '+str(len(result[1]['agent_actions'])))
            # print('number of predicates ='+str(len(result[1]['valid_models'][0].predicates)))
            # print('2AP = '+str(len(result[1]['agent_actions'])*len(result[1]['valid_models'][0].predicates)*2))
            preds.append(len(result[1]['valid_models'][0].predicates))
            actions.append(len(result[1]['agent_actions']))
            pal_tuples.append(result[1]['pal_tuple_count'])
            grid_size.append(grid[0]*grid[1])
            num_queries.append(result[1]['query_count'])
            time.append(result[1]['time'])
            
            sheet.write(i+1,1,grid[0]*grid[1])
            sheet.write(i+1,2,len(result[1]['valid_models'][0].predicates))
            sheet.write(i+1,3,len(result[1]['agent_actions']))
            sheet.write(i+1,4,result[1]['pal_tuple_count'])
            sheet.write(i+1,5,result[1]['query_count'])
            sheet.write(i+1,6,result[1]['time'])
        wb.save('sample_results.xls')  
        print('grid_size:  '+str(grid_size))
        print('preds:  '+str(preds))
        print('actions:  '+str(actions))
        print('pal_tuples:  '+str(pal_tuples))
        print('num_queries:  '+str(num_queries))
        print('time:  '+str(time))

    check_results = False
    for grid in grids:
        if  grid in domains[domain]:
              continue
        process = sb.Popen(['mkdir',"../gvg_agents/files/"+domain+"/"+str(grid[0])+'_'+str(grid[1])+"/"])
        rmfiles = "../gvg_agents/files/"+domain+"/"+str(grid[0])+'_'+str(grid[1])+"/"
        print("removed files")
        try:
            for f in os.listdir(rmfiles):
                print(f)
                try:
                    os.remove(os.path.join(rmfiles,f))  
                except IsADirectoryError:
                    continue
        except FileNotFoundError as e:
            embed()
        r = grid[0]
        c = grid[1]
        max_w = int(r*c*0.2)
        max_w = 0
        min_w = int(r*c*0.1)
        file = "../gvg_agents/files/"+domain+"/results/result"+str(grid[0])+"x"+str(grid[1])

        main(domain,check_results,file,r,c,min_w,max_w) 
        domains[domain].append(grid)
            
            
        
            


    
