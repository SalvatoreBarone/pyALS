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

for v in `find ${directory}/flat -name '*.v' | sort`; 
do 
    vsim -c -do "do do_sim.tcl ${toplevel} ${v} tb.v ${v}.sdf ${v}.vcd gscl45nm.v"
done;
