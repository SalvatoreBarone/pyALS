set source_file [lindex $argv 0]
set top [lindex $argv 1]
set lut_report [lindex $argv 2]
set pwr_report [lindex $argv 3]
set part_id [lindex $argv 4]
read_verilog $source_file 
synth_design -top $top -part $part_id
report_utilization -file $lut_report
create_clock -name clk_virt -period 1
report_power -file $pwr_report
