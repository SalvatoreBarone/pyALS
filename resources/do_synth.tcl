puts $hdl_source
puts $top_module
set leakage_optimization true
set dynamic_optimization true
set compile_clock_gating_through_hierarchy true
read_file -autoread -format verilog $hdl_source -top $top_module
current_design $top_module
analyze -format verilog $hdl_source
elaborate $top_module
compile_ultra
report_area > ./area.txt
report_power > ./power.txt
quit
