#! /bin/bash
#
# collect_dns.sh
# Copyright (C) 2024 TU Dresden
#
# Distributed under terms of the MIT license.
#

SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
REQUESTS=${REQUESTS:-${SCRIPT_DIR}/input_datasets/bq-results-20240930-154613-1727711199326_tabbed.csv}

PROCS=$(grep -c '^processor' /proc/cpuinfo)
if [ $PROCS -gt 64 ]; then
    # leave some resources to collegues ;-)
    PROCS=$(( (PROCS * 3) / 4))
fi

DATABASE="${SCRIPT_DIR}/output_datasets/dns-responses.db"
DOH_UPSTREAM=https://dns.google/dns-query

while getopts "d:D:" opt; do
    case "${opt}" in
        d)  DATABASE="${OPTARG}";;
        D)  DOH_UPSTREAM="${OPTARG}";;
    esac
done

collect_dns() {
    "${SCRIPT_DIR}"/collect_dns.py "${DOH_UPSTREAM}" "${DATABASE}" "$1"
}

export -f collect_dns
export SCRIPT_DIR
export DATABASE
export DOH_UPSTREAM

awk -F'\t' 'NR > 1 {print $2}' "${REQUESTS}" | parallel -j${PROCS} collect_dns
