# Interactive Capability Model Learning (iCaML)

This repository contains the code for the following paper:

Discovering User-Interpretable Capabilities of Black-Box Planning Agents.<br/>
[Pulkit Verma](https://pulkitverma.net), 
[Shashank Rao Marpally](https://marpally-raoshashank.netlify.app/),
[Siddharth Srivastava](http://siddharthsrivastava.net/). <br/>
Proceedings of the 19th International Conference on Principles of Knowledge Representation and Reasoning, 2022. <br/>

[Paper](https://aair-lab.github.io/Publications/vms_kr22.pdf) | [Video](https://youtu.be/OLxlB3pcjH0) | [Slides](https://pulkitverma.net/assets/pdf/vms_kr22/vms_kr22_slides.pdf)
<br />


## Directory Structure

```
|-- dependencies/
|   |-- FF/
|   |-- pddlgym/
|   |-- VAL/
|-- gvg_agents/
|-- src/
|   |-- agent.py
|   |-- config.py
|   |-- post_processing.py
|   |-- main.py
|   |-- interrogation/
|   |-- lattice/
|   |-- query/
|   |-- sim/
|   |-- utils/
|-- README.md
```

- dependencies: This directory includes the external software used to run the code. This includes FF, VAL, and PDDLGym. 
  - FF: https://fai.cs.uni-saarland.de/hoffmann/ff/FF-v2.3.tgz
  - PDDLGym: https://github.com/tomsilver/pddlgym
  - VAL: https://github.com/KCL-Planning/VAL

- dependencies: Place all the domains in this directory. There must be a directory for each domain containing: 
  - domain.pddl (domain file for that domain), and 
  - instances directory containing the problem files for that domain.

- gvg_agents: This has domain specific data including some results.

- src: This directory stores the source code for iCaML. It contains 4 files:
  - agent.py: Contains the agent code.
  - config.py: Declares the configuration parameters.
  - post_processing.py: Post Processing code for the learned pddl.
  - main.py : Contains the main driver code which runs the code end-to-end.

  src also contains code structured into following sub-directories:
  - interrogation: Contains the iCaML code.
  - lattice: Contains the model and lattice classes.
  - query: Contains the plan outcome query code.
  - sim: Simulator specific code. Contains a separate agent file for each simulator domain.
  - utils: Contains general utilities.

## Configuration

Configuration parameters are set in src/config.py

- FF_PATH and VAL_PATH stores relative path of FF and VAL respectively.
- PLANNER specifies which planner to use. Set it to FF only.

## How to Run

1. Install the required software
```
pip3 install -r requirements.txt 
```
2. Download FF, FD, and VAL and place in dependencies directory. Compile FF and FD.

3. Run main.py
```
cd src
python3 main.py
```

Please note that this is research code and not yet ready for public delivery, hence most parts are not documented.

In case you encounter any issues or bugs, please email verma.pulkit@asu.edu

# Citation
```
@inproceedings{verma2022discovering,
  author    = {Verma, Pulkit and Marpally, Shashank Rao and Srivastava, Siddharth},
  title     = {Discovering User-Interpretable Capabilities of Black-Box Planning Agents},
  booktitle = {Proceedings of the 19th International Conference on Principles of Knowledge Representation and Reasoning},
  year      = {2022}
}
```
