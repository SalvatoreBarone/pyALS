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

set top_module $1
set flat_netlist $2
set tb_file $3
set sdf_file $4
set vcd_file $5
set cell_library $6
set saif_file $7

# Set Library
vlib work

# Compile Library
vlog -reportprogress 300 -work work $cell_library

# Compile Netlist
vlog -reportprogress 300 -work work $flat_netlist

# Compile Testbench
vlog -reportprogress 30 -work work $tb_file

# Start Simulation
vsim -sdftyp tb_$top_module=$sdf_file -sdfnoerror -novopt -t 10ps work.tb_$top_module

# Write  Switching Activity to .vcd file
vcd file $vcd_file
vcd add -r /tb_$top_module/*
power add -r /tb_$top_module/*

# Start Simulation 
run -all
power report -all -bsaif $saif_file
quit -sim


