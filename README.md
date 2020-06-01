# GPU-Accelerated-Logic-Re-simulation





<!-- TABLE OF CONTENTS -->
## Table of Contents

* [Main Project Goals and Milestones](#main-project-goals-and-milestones)
* [General Framework](#general-framework)
* [Files and Formats](#files-and-formats)

<!-- ABOUT THE PROJECT -->
## Main project goals and milestones

Project objective:- Develop a GPU-accelerated, timing-aware, 4 value (0; 1; x; z) logic simulator for replaying RTL traces on gate-level netlists.

Required achievement:- A speed up in re/simulation tasks as compared to CPU based implementations/softwares.


### General Framework
The figure below shows the general structure of the project and deliverables. The boxes in red contain items that are expected to be submitted from us. As we progress along the project, the following questions should be answered at each step. 

1. What are the formats and structures of the files (gv, vcd, sdf, vlib, saif) that are given as inputs or expected as outputs?

2. What preprocessing result is needed as input for the simulation task? What file type and what content or information should be included in order to carry out the simulation.

3. How can the simulation leverage the GPU features and what should be included in the output files?


### Files and file formats

• .gv file:- A gate level netlist description of the design

• .sdf file:- describes the delays of each gate in the design

• .vlib file:- A standard cell library which describes the behavior of each standard cell gate in the design

• .vcd file:- Contains waveforms of the primary and pseudo-primary inputs of the design for the duration of the testbench. This file is both an input and expected output of our simulator.

• .saif file:- Contains the time nets were of value 0, 1, x, or z (T0, T1, TX, TZ) for all nets in the design for the duration of the specified timestamps given for the testbench.

