#!/usr/bin/env bash
#
# Copyright (C) 2024 TU Dresden
#
# Distributed under terms of the MIT license.
#

SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

PROCS=$(grep -c '^processor' /proc/cpuinfo)
if [ $PROCS -gt 64 ]; then
    # leave some resources to collegues ;-)
    PROCS=$(( (PROCS * 3) / 4))
fi
EXCLUDE_FORMAT_FILE="$(mktemp)"
while true; do
    case $1 in
    -e)  echo "$2" >> ${EXCLUDE_FORMAT_FILE}
         shift
         shift
         ;;
    *)   break;;
    esac
done

if [ $# -lt 3 ]; then
    echo "Usage: $0 <base format> <input file> <output file> [*-e <excluded formats>]" >&2
    exit 1
fi
BASE_FORMAT="$1"
INPUT_FILE="$2"
OUTPUT_FILE="$3"

"${SCRIPT_DIR}/compute_encoding_metrics.py" --header --exclude-format-file "${EXCLUDE_FORMAT_FILE}" "${BASE_FORMAT}" "${INPUT_FILE}" | \
    pigz > "${OUTPUT_FILE}"

compute_encoding_metrics() {
    "${SCRIPT_DIR}/compute_encoding_metrics.py"  --exclude-format-file "${EXCLUDE_FORMAT_FILE}" "${BASE_FORMAT}" "${INPUT_FILE}" 
}

export SCRIPT_DIR
export EXCLUDE_FORMAT_FILE
export BASE_FORMAT
export INPUT_FILE
export -f compute_encoding_metrics


zcat "${INPUT_FILE}" | \
    parallel --env EXCLUDE -j${PROCS} --pipe --line-buffer compute_encoding_metrics | \
    pigz >> "${OUTPUT_FILE}"
