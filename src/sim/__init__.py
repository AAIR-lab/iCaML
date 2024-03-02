import os
import sys

sys.path.append(os.path.abspath(os.path.dirname(__file__) + '/' + '../../dependencies'))
sys.path.append(os.path.abspath(os.path.dirname(__file__)+'/' + '../../GVGAI-master/clients/GVGAI-PythonClient/src/'))
sys.path.append(os.path.abspath(os.path.dirname(__file__)+'/' + '../../GVGAI-master/clients/GVGAI-PythonClient/src/utils/'))

#import pddlgym

from .sim_utils import gym_to_iaa_dict
from .sim_utils import problem_file_header
from .sim_utils import get_contours
from .sim_utils import calculate_color
from .sim_utils import Cell

from .predicate_classifier import StateHelper
