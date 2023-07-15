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

mkdir -p ${directory}/flat

source /opt/source.synopsys
source /opt/source.mentor
echo "Area (nm²);Internal Power (mW);Switching Power (mW);Total Power (mW)" > ${directory}/synth_data.csv;
for v in `find ${directory} -name 'variant*.v' | sort`; 
do 
    dc_shell -f do_synth.tcl -x "set hdl_source ${v}; set top_module ${toplevel}; set flat_netlist ${directory}/flat/$(basename ${v}); set sdf_file ${directory}/flat/$(basename ${v}).sdf; set sdc_file ${directory}/flat/$(basename ${v}).sdc"
    area=`cat area.txt | grep "Combinational area:" | sed -r "s/[^0-9.]*//g"`
	int_pwr=`grep "Total   " power.txt | sed -e's/  */ /g' | cut -d " " -f2`
	swc_pwr=`grep "Total   " power.txt | sed -e's/  */ /g' | cut -d " " -f4`
	tot_pwr=`grep "Total   " power.txt | sed -e's/  */ /g' | cut -d " " -f8`
    echo "${area};${int_pwr};${swc_pwr};${tot_pwr}" >> ${directory}/synth_data.csv;
	rm area.txt power.txt *.pvl *.syn *.mr
done;
cat ${directory}/metrics.csv | cut -d ";" -f1-15 > ${directory}/fitness.csv
paste -d ';' ${directory}/fitness.csv ${directory}/synth_data.csv > ${directory}/synthesis_results.csv
