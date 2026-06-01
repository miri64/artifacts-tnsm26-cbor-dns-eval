#!/usr/bin/env bash
#
# Copyright (C) 2024-26 TU Dresden
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

"${SCRIPT_DIR}"/collect_from_tls_data.py --header
zcat "${1}" | awk 'OFS="\t" {print "'"${1}"'",NR,$0}' | \
    parallel --progress --line-buffer -j"${PROCS}" --spreadstdin --round-robin \
        "${SCRIPT_DIR}"/collect_from_tls_data.py
