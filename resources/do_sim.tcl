# Copyright 2021-2022 Salvatore Barone <salvatore.barone@unina.it>

# This is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation; either version 3 of the License, or any later version.

# This is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
# more details.

# You should have received a copy of the GNU General Public License along with
# RMEncoder; if not, write to the Free Software Foundation, Inc., 51 Franklin
# Street, Fifth Floor, Boston, MA 02110-1301, USA.

set bench_name {{ items["top_level_entity"] }}

# Set Library
vlib work

# Compile Library
vlog -reportprogress 300 -work work {{ items["lib_v"] }}

# Compile Netlist
#vlog -reportprogress 300 -work work ./$bench_name/source/$bench_name\_comb_syn.v
vlog -reportprogress 300 -work work {{ items["flat_netlist"] }}

# Compile Testbench
#vlog -reportprogress 30 -work work ./$bench_name/results/tb_$bench_name\_comb_syn.v
vlog -reportprogress 30 -work work {{ items["tb_file"] }}.v


# Start Simulation
#vsim -sdftyp $bench_name\_1_test/dut=./$bench_name/results/$bench_name\_comb_syn.sdf -sdfnoerror -t 10ps -novopt work.$bench_name\_1_test
vsim -sdftyp {{ items["top_level_entity"] }}_test/dut={{ items["sdf_file"] }} -sdfnoerror -t 10ps -novopt work.{{ items["top_level_entity"] }}_test

# Write  Switching Activity to .vcd file
#vcd file ./$bench_name/results/tb_$bench_name\_comb_syn.vcd
vcd file {{ items["vcd_file"] }}
#vcd add -r /$bench_name\_1_test/dut/*
vcd add -r /{{ items["top_level_entity"] }}_test/dut/*
#power add -r /$bench_name\_1_test/dut/*
power add -r /{{ items["top_level_entity"] }}_test/dut/*

# Start Simulation 
run -all
quit


