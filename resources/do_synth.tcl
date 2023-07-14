puts $hdl_source
puts $top_module
puts $flat_netlist
puts $sdf_file
set leakage_optimization true
set dynamic_optimization true
set compile_clock_gating_through_hierarchy true
read_file -autoread -format verilog $hdl_source -top $top_module
current_design $top_module
analyze -format verilog $hdl_source
elaborate $top_module
compile_ultra

write -hierarchy -format verilog -output $flat_netlist
write_sdf $sdf_file

report_area > ./area.txt
report_power > ./power.txt
quit
