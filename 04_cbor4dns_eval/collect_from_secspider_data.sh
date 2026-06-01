#!/usr/bin/env bash
#
# Copyright (C) 2024 TU Dresden
#
# Distributed under terms of the MIT license.
#

SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

PROCS=$(grep -c '^processor' /proc/cpuinfo)
OUTPUT_DATASETS="${SCRIPT_DIR}/output_datasets"

if [ $# -lt 1 ]; then
    echo "usage: $0 <input ndjson file>" >&2
    exit 1
fi

export INPUT_DATASETS="$(dirname "$(readlink -f "${1}")")"

function prep_join() {
    zcat "${1}" | awk '
        BEGIN{FS=OFS="\t"}
        NR == 1 {print "LINE",$0}
        # remove stray "s in dataset while constructing
        NR > 1 {print NR-1,$0}'
}

"${SCRIPT_DIR}"/collect_from_secspider_data.py --header "${1}"
join -t $'\t' --header -j 2 <(prep_join "${1}") <(prep_join "${1}") | \
    parallel --compress --line-buffer -j"${PROCS}" --spreadstdin --round-robin \
        "${SCRIPT_DIR}"/collect_from_secspider_data.py "${1}"
