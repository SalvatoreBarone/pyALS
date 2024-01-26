#!/bin/bash
set -e
usage() {
  echo "Usage: $0 -x path_to_vivado [-d path_to_target_directory | -l ]";
  echo "-l: enable long format (for arithmetic circuits only)";
  exit 1;
}

do_synth() {
	DIRECTORY=$1
	COLLECT_ARITH_METRICS=$2
	EXACT_SOURCE=$(find ${DIRECTORY} -mindepth 1 -maxdepth 1 -name '*.v');
	TOP_MODULE_NAME=${EXACT_SOURCE%.*}; 
	TOP_MODULE_NAME=${TOP_MODULE_NAME##*/};

	echo -e "*************************************************************************************************************************"
	echo "* Directory: ${DIRECTORY}"
	echo "*     Source: ${EXACT_SOURCE}"
	echo "*     Module: ${TOP_MODULE_NAME}"
	
	for SUBDIRECTORY in $(find ${DIRECTORY} -mindepth 1 -maxdepth 1 -type d | sort);
	do
		echo "*     Subdirectory: ${SUBDIRECTORY}"  
		rm -f ${SUBDIRECTORY}/synth_report.txt 
		for AXC_SOURCE in $(find ${SUBDIRECTORY} -name '*.v' | sort); 
		do
			echo "*         Synthesizing ${AXC_SOURCE}"
			${VIVADO_BIN} -mode batch -source fpga_synth.tcl -notrace -tclargs ${AXC_SOURCE} ${TOP_MODULE_NAME} report_lut.txt report_pwr.txt  > /dev/null;
			REQUIRED_LUTS=$(grep "Slice LUTs\*" < report_lut.txt | cut -d '|' -f 3);
			POWER_CONSUMPTION=$(grep "Total On-Chip Power" < report_pwr.txt | cut -d '|' -f 3);
			echo "${AXC_SOURCE};${REQUIRED_LUTS};${POWER_CONSUMPTION}" >> ${SUBDIRECTORY}/synth_report.txt;
		done;
		if [ "$COLLECT_ARITH_METRICS" = true ] ; then
			cat ${SUBDIRECTORY}/metrics.csv | cut -d ';' --fields=1,2,3,4,5,6,7,8,9,10,11,12,13,14 > tmp1.txt
		else
			cat ${SUBDIRECTORY}/metrics.csv | cut -d ';' --fields=1,2,3,4,5 > tmp1.txt
		fi
		cat ${SUBDIRECTORY}/synth_report.txt | cut -d ';' --fields=2,3 | sed "s/\\s\+//g" > tmp2.txt;
		sed -i "1 i\LUTs;Power" tmp2.txt
		paste -d ';' tmp1.txt tmp2.txt > ${SUBDIRECTORY}/synthesis_results.csv
		rm -rf tmp1.txt tmp2.txt ${SUBDIRECTORY}/synth_report.txt;
		echo "*         Generating report file ${SUBDIRECTORY}/synthesis_results.csv"
	done

	echo "*     Synthesizing ${EXACT_SOURCE}"
	${VIVADO_BIN} -mode batch -source fpga_synth.tcl -notrace -tclargs "${EXACT_SOURCE}" "${TOP_MODULE_NAME}" report_lut.txt report_pwr.txt > /dev/null;
	REQUIRED_LUTS=$(grep "Slice LUTs\*" < report_lut.txt | cut -d '|' -f 3);
	POWER_CONSUMPTION=$(grep "Total On-Chip Power" < report_pwr.txt | cut -d '|' -f 3);
	echo "Source;LUTs;Power" > ${DIRECTORY}/synth_report.csv;
	echo "${EXACT_SOURCE};${REQUIRED_LUTS};${POWER_CONSUMPTION}" >> ${DIRECTORY}/synth_report.csv;
	echo -e "*************************************************************************************************************************\n\n\n"
}

COLLECT_ARITH_METRICS=false
while getopts "x:d:l" o; do
    case "${o}" in
        x)
            VIVADO_BIN=${OPTARG}
            ;;
		d)
			DIRECTORY=${OPTARG}
            ;;
		l)  COLLECT_ARITH_METRICS=true
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

rm -rf .Xil
VIVADO_BIN=$(realpath $VIVADO_BIN)

if [ -z "${DIRECTORY}" ] ; then
	for DIRECTORY in $(find . -mindepth 1 -maxdepth 1 -type d | sort);
	do
	   	do_synth $DIRECTORY $COLLECT_ARITH_METRICS	
	done
else
	do_synth $DIRECTORY $COLLECT_ARITH_METRICS
fi

rm -rf report_lut.txt report_pwr.txt vivado*.jou vivado*.log .Xil
