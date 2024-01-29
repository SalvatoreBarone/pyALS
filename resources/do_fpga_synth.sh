#!/bin/bash
set -e
usage() {
  echo "Usage: $0 -x path_to_vivado -d path_to_target_directory -t top_module | -l ]";
  echo "-l: enable long format (for arithmetic circuits only)";
  exit 1;
}

COLLECT_ARITH_METRICS=false
while getopts "x:t:l" o; do
    case "${o}" in
        x)
            VIVADO_BIN=${OPTARG}
			VIVADO_BIN=$(realpath $VIVADO_BIN)
            ;;
		t)
			TOP_MODULE=${OPTARG}
			;;
		l)  
			COLLECT_ARITH_METRICS=true
			;;
        *)
            usage
            ;;
    esac
done
shift $((OPTIND-1))

if [ -z "${VIVADO_BIN}" ] ; then
    usage
fi
if [ -z "${TOP_MODULE}" ] ; then
    usage
fi

for AXC_SOURCE in $(find . -name 'variant*.v' | sort); 
do
	echo "* Synthesizing ${AXC_SOURCE}"
	${VIVADO_BIN} -mode batch -source fpga_synth.tcl -notrace -tclargs ${AXC_SOURCE} ${TOP_MODULE} report_lut.txt report_pwr.txt  > /dev/null;
	REQUIRED_LUTS=$(grep "Slice LUTs\*" < report_lut.txt | cut -d '|' -f 3);
	POWER_CONSUMPTION=$(grep "Total On-Chip Power" < report_pwr.txt | cut -d '|' -f 3);
	echo "${AXC_SOURCE};${REQUIRED_LUTS};${POWER_CONSUMPTION}" >> synth_report.txt;
done;
if [ "$COLLECT_ARITH_METRICS" = true ] ; then
	cat metrics.csv | cut -d ';' --fields=1,2,3,4,5,6,7,8,9,10,11,12,13,14 > tmp1.txt
else
	cat metrics.csv | cut -d ';' --fields=1,2,3,4,5 > tmp1.txt
fi
cat synth_report.txt | cut -d ';' --fields=2,3 | sed "s/\\s\+//g" > tmp2.txt;
sed -i "1 i\LUTs;Power" tmp2.txt
paste -d ';' tmp1.txt tmp2.txt > synthesis_results.csv
rm -rf tmp1.txt tmp2.txt synth_report.txt report_lut.txt report_pwr.txt vivado*.jou vivado*.log .Xil

