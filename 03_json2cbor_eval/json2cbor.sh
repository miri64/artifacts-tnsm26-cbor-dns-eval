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
export INPUT_PATH="${INPUT_PATH:-${SCRIPT_DIR}/jsons}"
export OUTPUT_PATH="${OUTPUT_PATH:-${SCRIPT_DIR}/cbors}"

if [ $# -lt 1 ]; then
    echo "usage: $0 <output file>" >&2
    exit 1
fi

export OUTPUT_FILE="$(readlink -f "${1}")"

"${SCRIPT_DIR}"/json2cbor.py --header > "${OUTPUT_FILE}"
find "${INPUT_PATH}" -type f | \
    parallel --line-buffer -j"${PROCS}" -I'{}' \
        "${SCRIPT_DIR}"/json2cbor.py '{}' >> "${OUTPUT_FILE}"
