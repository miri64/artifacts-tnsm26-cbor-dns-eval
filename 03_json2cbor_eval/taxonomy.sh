#!/usr/bin/env bash
#
# Copyright (C) 2025-26 TU Dresden
#
# Distributed under terms of the MIT license.
#

SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

if [ $# -lt 1 ]; then
    echo "usage: $0 <input file>" >&2
    exit 1
fi

# PROCS=$(grep -c '^processor' /proc/cpuinfo)
# if [ $PROCS -gt 64 ]; then
#     # leave some resources to collegues ;-)
#     PROCS=$(( (PROCS * 3) / 4))
# fi
PROCS=256


taxonomy() {
    JSON_FILENAME="$(echo "$1" | cut -d';' -f1)"
    if ! [ -f "/users/lenders/03_json2cbor_eval/jsons/${JSON_FILENAME}" ]; then
        echo "$1"
        return
    fi
    if ! echo "$1" | grep -q '\(github_api_[^;]\+\|stored_json\);;;;;'; then
        echo "$1"
        return
    fi
    TAX=$("${SCRIPT_DIR}/../utils/taxonomy.py" "/users/lenders/03_json2cbor_eval/jsons/${JSON_FILENAME}" | \
        sed "s/\['tier \([0-9]\+\)', '\(.\)\(.*\)', '\(.\)\(.*\)', '\(.\)\(.*\)'\]/\1;\U\2\E\3;\U\4\E\5;\U\6\E\7/g")
    if [ "${TAX}" = "['str', 'str', 'str', 'str']" ]; then
        echo "${TAX}" >&2
        return
    fi
    echo "$1" | sed "s/\(github_api_[^;]\+\|stored_json\);;;;;/\1;${TAX};/"
}

INPUT_FILE="${1}"

export -f taxonomy
export SCRIPT_DIR

taxonomy "$(grep 'harch/atlas\.json' "${INPUT_FILE}")"
