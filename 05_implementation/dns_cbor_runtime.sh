#!/usr/bin/env bash
#
# Copyright (C) 2024-26 TU Dresden
#
# Distributed under terms of the MIT license.
#

SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
INPUT_DATASETS=${INPUT_DATASETS:-${SCRIPT_DIR}/../04_cbor4dns_eval/output_datasets}
PROCS=$(grep -c '^processor' /proc/cpuinfo)
ITERATIONS=100
FLAGS=""

if [ $PROCS -gt 64 ]; then
    # leave some resources to collegues ;-)
    # PROCS=$(( (PROCS * 3) / 4))
    PROCS=32
fi

usage() {
    echo "Usage: $0 [-d|-p] [-t <tag number] -o <output_file>" >&2
}

while getopts 'dpho:t:' OPTION; do
  case "$OPTION" in
    d)  FLAGS="${FLAGS} -d"
      	;;
    p)  FLAGS="${FLAGS} -p"
        ;;
    t)  FLAGS="${FLAGS} -t ${OPTARG}"
        ;;
    h)  usage
        exit 1
        ;;
    o)  OUTPUT_FILE="${OPTARG}"
        ;;
    ?)  usage
        exit 1
        ;;
  esac
done

if [ -z "${OUTPUT_FILE}" ]; then
    usage
    exit 1
fi

zcat "${INPUT_DATASETS}"/dns_data_iot.csv.gz | \
    "${SCRIPT_DIR}/dns_cbor_runtime.py" ${FLAGS} -i ${ITERATIONS} --header | \
    pigz > "${OUTPUT_FILE}"

zcat "${INPUT_DATASETS}"/dns_data_iot.csv.gz | \
    parallel -j$PROCS --spreadstdin --line-buffer \
        "${SCRIPT_DIR}/dns_cbor_runtime.py" ${FLAGS} -i ${ITERATIONS} | \
    pigz >> "${OUTPUT_FILE}"
