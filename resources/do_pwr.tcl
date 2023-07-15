set power_enable_analysis true
set power_analysis_mode time_based

#link design
set search_path         " . "
read_verilog            $flat_netlist
current_design          $top_module
link
read_sdc $sdc_file

# read switching activity file
read_vcd $vcd_file -strip_path tb_$top_module/dut

# check/update/report power 
check_power
set_power_analysis_options -waveform_format fsdb -waveform_output vcd
update_power
report_power -net_power -cell_power -hierarchy > report_power_full.txt
report_power > report_power.txt

quit

