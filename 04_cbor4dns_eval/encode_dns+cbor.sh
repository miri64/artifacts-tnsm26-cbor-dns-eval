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
PYTHON_ARGS=""

while getopts ":t:" o; do
    case "${o}" in
        t)
            PYTHON_ARGS="${PYTHON_ARGS} -t ${OPTARG}"
            shift 2
            ;;
        *)  ;;
    esac
done

if [ $# -ne 2 ]; then
    echo "Usage: $0 [-t <tag number>] <input file> <output file>" >&2
    exit 1
fi

INPUT_FILE="$1"
OUTPUT_FILE="$2"

"${SCRIPT_DIR}/encode_dns+cbor.py" ${PYTHON_ARGS} --header "${INPUT_FILE}" | \
    pigz > "${OUTPUT_FILE}"

zcat "${INPUT_FILE}" | \
    parallel -j${PROCS} --pipe --line-buffer \
    "${SCRIPT_DIR}/encode_dns+cbor.py" ${PYTHON_ARGS} ${INPUT_FILE} | \
        pigz >> "${OUTPUT_FILE}"
