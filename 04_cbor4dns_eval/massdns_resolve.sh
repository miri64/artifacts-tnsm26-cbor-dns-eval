#!/bin/bash

SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

EXP="${EXP:-}"
MASSDNS_DIR="${SCRIPT_DIR}/massdns"
RESULTS_DIR="${RESULTS_DIR:-${SCRIPT_DIR}/input_datasets/tranco}"
PROCS="$(grep -c '^processor' /proc/cpuinfo)"
TRANCO_SET=KJ49W
RESOLVERS=( "8.8.8.8" "1.1.1.1" "9.9.9.9" )
CNAME_ITERATION=1
RRTYPES="-t AAAA -t A -t HTTPS -t NS -t PTR -t DS -t RRSIG -t DNSKEY -t NSEC -t NSEC3"
RRTYPES_NAMES=$(echo "${RRTYPES}" | sed -E 's/ ?-t /_/g')

if [ $# -gt 0 ]; then
    SNIFF_IFACE=$1
fi

mkdir -p "${RESULTS_DIR}"

if [ ! -f "${RESULTS_DIR}/tranco_${TRANCO_SET}_full.csv" ]; then
    wget -O "${RESULTS_DIR}/tranco_${TRANCO_SET}_full.csv" "https://tranco-list.eu/download/${TRANCO_SET}/full" \
        2>&1 || exit 1
fi

echo -n "" > "${SCRIPT_DIR}/resolvers.txt"

for RESOLVER in ${RESOLVERS[@]}; do
    echo "${RESOLVER}" >> "${SCRIPT_DIR}/resolvers.txt"
done

if [ -n "${SNIFF_IFACE}" ]; then
    tshark -i "${SNIFF_IFACE}" \
        -w "${RESULTS_DIR}/tranco_${TRANCO_SET}_full_${RRTYPES_NAMES}${EXP}.pcapng" "port 53" &
    TSHARK_PID=$!
    sleep 5  # make sure tshark listens
fi

awk -F, '{print $2}' "${RESULTS_DIR}/tranco_${TRANCO_SET}_full.csv" | sed 's/\r$//' |
    "${MASSDNS_DIR}/bin/massdns" --status-format json -r "${SCRIPT_DIR}/resolvers.txt" ${RRTYPES} -o J | \
    sed "s/}\$/,\"cname_iteration\":${CNAME_ITERATION}}/" \
    > "${RESULTS_DIR}/tranco_${TRANCO_SET}_full_${RRTYPES_NAMES}${EXP}_${CNAME_ITERATION}.ndjson"

while grep -q -e "CNAME" \
        "${RESULTS_DIR}/tranco_${TRANCO_SET}_full_${RRTYPES_NAMES}${EXP}_${CNAME_ITERATION}.ndjson"; do
     CNAME_ITERATION=$((CNAME_ITERATION + 1))
    cat "${RESULTS_DIR}/tranco_${TRANCO_SET}_full_${RRTYPES_NAMES}${EXP}_$(( CNAME_ITERATION - 1 )).ndjson" | \
    jq -r '.data[][] | select (.type == "CNAME") | .data' | sort -u | \
        "${MASSDNS_DIR}/bin/massdns" --status-format json -r "${SCRIPT_DIR}/resolvers.txt" ${RRTYPES} -o J | \
    sed "s/}\$/,\"cname_iteration\":${CNAME_ITERATION}}/" \
        > "${RESULTS_DIR}/tranco_${TRANCO_SET}_full_${RRTYPES_NAMES}${EXP}_${CNAME_ITERATION}.ndjson" \

    if [ ${CNAME_ITERATION} -eq 10 ]; then
         break
    fi
done

if [ -n "${TSHARK_PID}" ]; then
    kill "${TSHARK_PID}"
fi

cat "${RESULTS_DIR}/tranco_${TRANCO_SET}_full_${RRTYPES_NAMES}${EXP}_"*.ndjson | xz \
    > "${RESULTS_DIR}/tranco_${TRANCO_SET}_full_${RRTYPES_NAMES}${EXP}.ndjson.xz"
