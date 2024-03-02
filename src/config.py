#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from enum import Enum, IntEnum

# Symbolic Agent Settings - Next 3 lines
is_simulator_agent = True   
ground_actions = True
domains = ["blocksworld", "logistics", "parking", "satellite", "barman",
           "gripper", "miconic", "rovers", "termes", "freecell"]
# Simulator Agent Settings - Next 2 lines
# domains = ["sokoban", "doors"]
# is_simulator_agent = True

domain_dir_gym = "../dependencies/pddlgym/pddl/"

VERBOSE = False

final_result_dir = "../temp_files/results/"
final_result_prefix = "final_result_aaai21"

Q_DOMAIN_FILE = "../temp_files/querymodel_domain.pddl"
Q_PROBLEM_FILE = "../temp_files/querymodel_problem.pddl"
Q_PLAN_FILE = "../temp_files/querymodel_plan.pddl"
Q_RESULT_FILE = "../temp_files/res.txt"
FD_SAS_FILE = "temp_files/sas_plan"
TEMP_FOLDER = "../temp_files/"
ALL_ACTION_FILE = "../temp_files/action_list.txt"
temp_plan_file = "../temp_files/querymodel_temp_plan.pddl"
agent_model_file = "../temp_files/agentmodel_domain.pddl"
DOMAINS_PATH = "../domains/"
temp_output_file = "../temp_files/temp_output.txt"
SIM_DOMAINS = ["sokoban", "doors"]
QUERY_SAVE_FILE = "../gvg_agents/files/"

image_resource_dir = TEMP_FOLDER + "image_resources/"

init_state_count = 1
save_random_states = True
RANDOM_STATE_FOLDER = "../random_states/"

VAL_PATH = "../dependencies/VAL/validate"
FF_PATH = "../dependencies/FF/"
FD_PATH = "../dependencies/FD/"

# Set FF for ffPlanner
# Set FD for fdPlanner
PLANNER = "FF"

if is_simulator_agent:
    NUM_PER_DOMAIN = 1
else:
    NUM_PER_DOMAIN = 10


class Location(IntEnum):
    PRECOND = 1
    EFFECTS = 2
    ALL = 3


class Literal(Enum):
    AN = -2
    NEG = -1
    ABS = 0
    POS = 1
    AP = 2
    NP = 3


render_random_states = False
num_random_states = 20
num_additional_states = 20

ignore_list = [[Literal.NEG, Literal.NEG], [Literal.POS, Literal.POS]]

pal_tuples_finalized = []
abs_actions_test = dict()
abs_preds_test = dict()


PROBLEM_DIR = "instances"
DOMAIN_FILE = "domain.pddl"
GEN_RESULT_FILE = TEMP_FOLDER + "gen_res.txt"
GEN_PLAN_FILE = TEMP_FOLDER + "gen_res.plan"
GEN_VAL_FILE = TEMP_FOLDER + "gen_res.val"
# VAL = "./dependencies/VAL/validate"
RANDOM_STATE_FOLDER = "../random_states/"
STORED_STATES_COUNT = 60
