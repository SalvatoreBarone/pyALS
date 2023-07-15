#!/bin/bash
usage() {
  echo "Usage: $0 -t top_level -d directory";
  exit 1;
}

while getopts "t:-l:-d:" o; do
    case "${o}" in
        t)
            toplevel=${OPTARG}
            ;;
        d)
            directory=${OPTARG}
            ;;
        *)
            usage
            ;;
    esac
done
shift $((OPTIND-1))

if [ -z "${toplevel}" ] || [ -z "${directory}" ] ; then
   usage
fi

source /opt/source.synopsys
source /opt/source.mentor

echo "Area (nm²);Internal Power (mW);Switching Power (mW);Total Power (mW)" > power_data.csv;
for v in `find ${directory}/flat -name '*.v' | sort`; 
do 
    vsim -c -do "do do_sim.tcl ${toplevel} ${v} tb.v ${v}.sdf ${v}.vcd gscl45nm.v"
    pt_shell -f do_pwr.tcl -x "set flat_netlist ${v}; set top_module ${toplevel}; set vcd_file ${v}.vcd; set sdc_file ${v}.vcd; set link_library gscl45nm.db"
    grep "combinational" report_power.txt | sed -e's/  */ /g' | cut -d " " -f2-5 | sed -e 's/ /;/g' >> power_data.csv
done;
